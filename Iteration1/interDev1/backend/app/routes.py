from pathlib import Path
from urllib.parse import unquote
from uuid import uuid4

from flask import Blueprint, jsonify, make_response, request
from flask_cors import CORS
from SPARQLWrapper import JSON, SPARQLWrapper
from werkzeug.utils import secure_filename
import os
import pycountry
import requests

UPLOAD_FOLDER = "./uploads"
ALLOWED_EXTENSIONS = {"pdf"}

GRAPHDB_REPOSITORY = os.getenv("GRAPHDB_REPOSITORY", "RCT")
SPARQL_QUERY_ENDPOINT = os.getenv(
    "SPARQL_QUERY_ENDPOINT", f"http://localhost:7200/repositories/{GRAPHDB_REPOSITORY}"
)
SPARQL_UPDATE_ENDPOINT = os.getenv(
    "SPARQL_UPDATE_ENDPOINT", f"{SPARQL_QUERY_ENDPOINT}/statements"
)
MAPPED_DATA_TTL_PATH = Path(
    os.getenv(
        "MAPPED_DATA_TTL_PATH",
        Path(__file__).resolve().parents[2] / "mapped_data.ttl",
    )
)

PREFIXES = """
PREFIX erct: <https://erct.adaptcentre.com/ontology#>
PREFIX ercgt: <http://www.semanticweb.org/ERCT#>
PREFIX gn: <http://www.geonames.org/ontology#>
PREFIX ex: <https://interdev.adaptcentre.com/id/>
PREFIX ns1: <http://example.org/people/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""

# Canonical API keys expected by the frontend.
PREDICATE_ALIASES = {
    "hasName": "Title",
    "State/Province_name": "State_Province_name",
    "Pre-Registration": "Pre_Registration",
}

FILTER_PREDICATES = {
    "Abstract": ["erct:Abstract", "ns1:Abstract"],
    "Authors": ["erct:Authors", "ns1:Authors"],
    "Sector": ["erct:Sector", "ns1:Sector"],
    "Title": ["erct:hasName", "ns1:Title"],
    "Keywords": ["erct:Keywords", "ns1:Keywords"],
    "Language": ["erct:Language", "ns1:Language"],
    "countryCode": ["gn:countryCode"],
}

CATEGORY_FIELDS = {
    "sector": ["erct:Sector", "ns1:Sector"],
    "country": ["gn:countryCode"],
    "countrycode": ["gn:countryCode"],
}

main = Blueprint("main", __name__)
CORS(main)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def sparql_escape(value):
    if value is None:
        return ""
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "")
    )


def get_sparql_client():
    return SPARQLWrapper(SPARQL_QUERY_ENDPOINT)


def trial_subject_candidates(trial_id):
    if not trial_id:
        return []
    trial_id = trial_id.split(":")[-1]
    return [
        f"ex:{trial_id}",
        f"ns1:{trial_id}",
        f"<urn:uuid:{trial_id}>",
        f"<https://interdev.adaptcentre.com/id/{trial_id}>",
    ]


def local_name(uri):
    if "#" in uri:
        raw_name = uri.rsplit("#", 1)[1]
    else:
        raw_name = uri.rsplit("/", 1)[-1]
    return unquote(raw_name)


def normalize_key(raw_key):
    key = local_name(raw_key)
    return PREDICATE_ALIASES.get(key, key)


def normalize_value(value):
    if isinstance(value, str):
        return value.replace("\u00a0", " ").strip()
    return value


def resolve_object_value(binding):
    predicate = binding["p"]["value"]
    object_value = binding["o"]["value"]
    object_type = binding["o"].get("type")
    object_label = binding.get("oLabel", {}).get("value")

    # Preserve API behavior for classification values now modelled as IRIs.
    if (
        object_type == "uri"
        and local_name(predicate) == "hasExternalClassification"
        and object_label
    ):
        return object_label

    return object_value


def clean_trial(trial):
    cleaned_trial = {}
    for key, value in trial.items():
        normalized_key = normalize_key(key)
        if isinstance(value, list):
            normalized_values = [normalize_value(item) for item in value]
            cleaned_trial[normalized_key] = ", ".join(
                [str(item) for item in normalized_values]
            )
        else:
            cleaned_trial[normalized_key] = normalize_value(value)
    return cleaned_trial


def build_filter_conditions(filters):
    conditions = []
    for predicate, values in filters.items():
        candidate_predicates = FILTER_PREDICATES.get(predicate)
        if not candidate_predicates:
            continue
        for index, value in enumerate(values):
            escaped_value = sparql_escape(value)
            predicate_block = " ".join(candidate_predicates)
            conditions.append(
                f"VALUES ?predicate_{predicate}_{index} {{ {predicate_block} }}\n"
                f"?s ?predicate_{predicate}_{index} \"{escaped_value}\" ."
            )
    return "\n".join(conditions)


def is_trial_type_filter():
    return """
    {
        ?s a erct:RandomisedControlledTrial .
    } UNION {
        ?s a ercgt:RandomisedControlledTrial .
    }
    """


@main.route("/search", methods=["GET"])
def search():
    return jsonify({"results": ["Item 1", "Item 2", "Item 3"]})


@main.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if not (file and allowed_file(file.filename)):
        return jsonify({"error": "File not allowed"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    return jsonify({"success": True, "filename": filename})


@main.route("/reload_knowledge_graph_data", methods=["POST"])
def reload_knowledge_graph_data():
    ttl_path = Path(request.args.get("path", str(MAPPED_DATA_TTL_PATH)))
    if not ttl_path.exists():
        return jsonify({"error": f"TTL file not found: {ttl_path}"}), 404

    clear_query = "CLEAR ALL"
    headers_update = {
        "Content-Type": "application/sparql-update",
        "Accept": "application/sparql-results+json",
    }
    headers_ttl = {"Content-Type": "text/turtle"}

    try:
        clear_response = requests.post(
            SPARQL_UPDATE_ENDPOINT, data=clear_query, headers=headers_update, timeout=60
        )
        clear_response.raise_for_status()

        with ttl_path.open("rb") as ttl_file:
            insert_response = requests.post(
                SPARQL_UPDATE_ENDPOINT,
                data=ttl_file.read(),
                headers=headers_ttl,
                timeout=120,
            )
        insert_response.raise_for_status()
    except requests.RequestException as error:
        return (
            jsonify(
                {
                    "error": "Failed to reload mapped_data.ttl into GraphDB",
                    "details": str(error),
                }
            ),
            500,
        )

    return jsonify(
        {
            "message": "Knowledge graph reloaded from mapped_data.ttl",
            "path": str(ttl_path),
            "repository": GRAPHDB_REPOSITORY,
        }
    )


@main.route("/download_knowledge_graph_data", methods=["GET"])
def download_knowledge_graph_data():
    sparql = get_sparql_client()
    trial_ids = request.args.getlist("trialIds")
    filters = request.args.to_dict(flat=False)
    filters.pop("trialIds", None)

    filter_conditions = build_filter_conditions(filters)
    subject_values = []
    for trial_id in trial_ids:
        subject_values.extend(trial_subject_candidates(trial_id))

    values_clause = ""
    if subject_values:
        values_clause = f"VALUES ?s {{ {' '.join(subject_values)} }}"

    query = f"""
    {PREFIXES}
    CONSTRUCT {{ ?s ?p ?o }}
    WHERE {{
        {values_clause}
        {is_trial_type_filter()}
        ?s ?p ?o .
        {filter_conditions}
    }}
    """

    sparql.setQuery(query)
    sparql.setReturnFormat("turtle")
    results = sparql.query().convert()

    response = make_response(results)
    response.headers["Content-Type"] = "text/turtle"
    return response


@main.route("/knowledge_graph_data", methods=["GET"])
def fetch_knowledge_graph_data():
    sparql = get_sparql_client()
    trial_ids = request.args.getlist("trialIds")
    limit = request.args.get("limit", default=500, type=int)
    filters = request.args.to_dict(flat=False)
    filters.pop("limit", None)
    filters.pop("trialIds", None)

    filter_conditions = build_filter_conditions(filters)
    subject_values = []
    for trial_id in trial_ids:
        subject_values.extend(trial_subject_candidates(trial_id))

    values_clause = ""
    if subject_values:
        values_clause = f"VALUES ?s {{ {' '.join(subject_values)} }}"

    query = f"""
    {PREFIXES}
    SELECT ?s ?p ?o ?oLabel
    WHERE {{
        {values_clause}
        {is_trial_type_filter()}
        ?s ?p ?o .
        OPTIONAL {{
            FILTER(?p = erct:hasExternalClassification)
            OPTIONAL {{ ?o rdfs:label ?oLabelRdfs . }}
            OPTIONAL {{ ?o erct:hasName ?oLabelName . }}
            OPTIONAL {{ ?o erct:hasUNSustainableGoal ?oLabelGoal . }}
            OPTIONAL {{ ?o erct:hasDAC ?oLabelDAC . }}
            BIND(COALESCE(?oLabelRdfs, ?oLabelName, ?oLabelGoal, ?oLabelDAC) AS ?oLabel)
        }}
        {filter_conditions}
    }}
    """

    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    processed_data = {}
    for result in results["results"]["bindings"]:
        subject = result["s"]["value"]
        trial_id = subject.rsplit("/", 1)[-1].split(":")[-1]

        if subject not in processed_data:
            processed_data[subject] = {"id": trial_id}

        predicate = result["p"]["value"]
        object_value = resolve_object_value(result)

        normalized_key = normalize_key(predicate)
        existing = processed_data[subject].get(normalized_key)
        if existing is None:
            processed_data[subject][normalized_key] = object_value
        elif isinstance(existing, list):
            existing.append(object_value)
        else:
            processed_data[subject][normalized_key] = [existing, object_value]

    required_fields = {"Abstract", "Authors", "Title"}
    filtered_data = [
        trial for trial in processed_data.values() if required_fields.issubset(trial.keys())
    ]
    cleaned_data = [clean_trial(trial) for trial in filtered_data]
    limited_data = cleaned_data[:limit]

    response_data = {"count": len(limited_data), "results": limited_data}
    response = make_response(jsonify(response_data))
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@main.route("/add_knowledge_graph_entry", methods=["POST"])
def add_knowledge_graph_entry():
    data = request.get_json() or {}
    entry_uuid = str(uuid4())

    field_map = {
        "Abstract": "erct:Abstract",
        "Authors": "erct:Authors",
        "Title": "erct:hasName",
        "Project_name": "erct:Project_name",
        "Sector": "erct:Sector",
        "Keywords": "erct:Keywords",
        "Evaluation_design": "erct:Evaluation_design",
        "countryCode": "gn:countryCode",
    }

    triples = []
    for field, predicate in field_map.items():
        value = data.get(field, "")
        if value:
            triples.append(f'{predicate} "{sparql_escape(value)}"')

    if triples:
        predicate_lines = " ;\n            ".join(triples)
        trial_statement = (
            f"ex:{entry_uuid} a erct:RandomisedControlledTrial ;\n"
            f"            {predicate_lines} ."
        )
    else:
        trial_statement = f"ex:{entry_uuid} a erct:RandomisedControlledTrial ."

    query = f"""
    {PREFIXES}
    INSERT DATA {{
        {trial_statement}
    }}
    """

    headers = {
        "Content-Type": "application/sparql-update",
        "Accept": "application/sparql-results+json",
    }

    try:
        response = requests.post(
            SPARQL_UPDATE_ENDPOINT, data=query, headers=headers, timeout=60
        )
        response.raise_for_status()
        return jsonify({"message": "Entry added successfully", "uuid": entry_uuid})
    except requests.RequestException as error:
        return (
            jsonify({"error": "Failed to execute query", "details": str(error)}),
            500,
        )


@main.route("/knowledge_graph_trial", methods=["GET"])
def fetch_specific_knowledge_graph_trial():
    trial_id = request.args.get("trialId")
    if not trial_id:
        return jsonify({"error": "trialId parameter is required"}), 400

    sparql = get_sparql_client()
    subject_candidates = trial_subject_candidates(trial_id)
    query = f"""
    {PREFIXES}
    SELECT ?s ?p ?o ?oLabel
    WHERE {{
        VALUES ?s {{ {' '.join(subject_candidates)} }}
        {is_trial_type_filter()}
        ?s ?p ?o .
        OPTIONAL {{
            FILTER(?p = erct:hasExternalClassification)
            OPTIONAL {{ ?o rdfs:label ?oLabelRdfs . }}
            OPTIONAL {{ ?o erct:hasName ?oLabelName . }}
            OPTIONAL {{ ?o erct:hasUNSustainableGoal ?oLabelGoal . }}
            OPTIONAL {{ ?o erct:hasDAC ?oLabelDAC . }}
            BIND(COALESCE(?oLabelRdfs, ?oLabelName, ?oLabelGoal, ?oLabelDAC) AS ?oLabel)
        }}
    }}
    """

    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    processed_data = {}
    subject_value = None
    for result in results["results"]["bindings"]:
        subject_value = result["s"]["value"]
        predicate = normalize_key(result["p"]["value"])
        object_value = resolve_object_value(result)
        existing = processed_data.get(predicate)
        if existing is None:
            processed_data[predicate] = object_value
        elif isinstance(existing, list):
            existing.append(object_value)
        else:
            processed_data[predicate] = [existing, object_value]

    if subject_value is None:
        return jsonify({"error": "Trial not found"}), 404

    response_data = {
        "id": subject_value.rsplit("/", 1)[-1].split(":")[-1],
        "data": clean_trial(processed_data),
    }
    response = make_response(jsonify(response_data))
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@main.route("/categories", methods=["GET"])
def fetch_categories():
    category = request.args.get("category", default="Sector", type=str)
    category_key = category.lower()
    category_fields = CATEGORY_FIELDS.get(category_key, [f"erct:{category}"])

    sparql = get_sparql_client()
    predicate_values = " ".join(category_fields)
    query = f"""
    {PREFIXES}
    SELECT DISTINCT ?value
    WHERE {{
        {is_trial_type_filter()}
        VALUES ?categoryPredicate {{ {predicate_values} }}
        ?trial ?categoryPredicate ?value .
    }}
    """

    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    categories = [{"name": row["value"]["value"]} for row in results["results"]["bindings"]]

    if category_key in {"country", "countrycode"}:
        mapped_categories = []
        seen_codes = set()
        for row in results["results"]["bindings"]:
            code = row["value"]["value"].strip().upper()
            if not code or code in seen_codes:
                continue

            country = pycountry.countries.get(alpha_2=code)
            display_name = country.name if country else code
            mapped_categories.append({"name": display_name, "code": code})
            seen_codes.add(code)

        categories = sorted(mapped_categories, key=lambda item: item["name"])

    response_data = {"count": len(categories), "results": categories}
    response = make_response(jsonify(response_data))
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


if __name__ == "__main__":
    main.run(debug=True, port=5000)
