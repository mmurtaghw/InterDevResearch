# Routes.py

from flask import Flask, Blueprint, jsonify, request, make_response
from werkzeug.utils import secure_filename
import os
from SPARQLWrapper import JSON, SPARQLWrapper, POST
import uuid
import requests
from flask_cors import CORS
from flask import send_from_directory
import pycountry
from openai import OpenAI
from dotenv import load_dotenv 
from pdfminer.high_level import extract_text
from rdflib import Graph, RDF, URIRef
import google.generativeai as genai
import anthropic
from datetime import datetime
import time 
import re
import json
import traceback
from typing import Any, Dict, List, Tuple
from http.client import IncompleteRead
import threading
from threading import Lock
import hashlib

from app.semantic_search import SemanticSearcher

UPLOAD_FOLDER = '/home/mwhite/interDev/backend/uploads'

ALLOWED_EXTENSIONS = {'pdf'}

ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(ENV_PATH)

# STATIC_FOLDER = os.path.abspath("/home/mwhite/interDev/interface/interface")

# print(STATIC_FOLDER)

app = Flask(__name__, static_url_path=None)


app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER 

# Allow CORS for the deployed interface domain(s)
CORS(app, resources={
    r"/*": {"origins": [
        "https://interdev2.adaptcentre.ie",
        "http://vma49.scss.tcd.ie",
        "http://vma47.scss.tcd.ie",
        "http://vma45.scss.tcd.ie",
    ],
    "allow_headers": ["Content-Type", "X-Participant-Name"]}
})


main = Blueprint('main', __name__)


# CORS(main)  # Not needed as CORS is already enabled globally

client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
anthropicClient = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

SEMANTIC_CACHE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "semantic_cache.json"
)
SEMANTIC_SPARQL_ENDPOINT = os.getenv(
    "GRAPHDB_SPARQL_ENDPOINT", "http://vma47.scss.tcd.ie:7200/repositories/erct"
)
SEMANTIC_SCORE_THRESHOLD = float(os.getenv("SEMANTIC_SEARCH_MIN_SCORE", "0.2"))
SEMANTIC_MAX_TOP_K = int(os.getenv("SEMANTIC_SEARCH_TOP_K", "60"))
semantic_searcher = SemanticSearcher(
    client=client,
    sparql_endpoint=SEMANTIC_SPARQL_ENDPOINT,
    cache_path=SEMANTIC_CACHE_PATH,
)
_SEMANTIC_CACHE_WARMED = False


def _warm_semantic_cache_async():
    global _SEMANTIC_CACHE_WARMED
    if _SEMANTIC_CACHE_WARMED:
        return

    def _warm():
        global _SEMANTIC_CACHE_WARMED
        try:
            semantic_searcher.search("cache warmup", top_k=1)
        except Exception as exc:
            print(f"[semantic-search] Warmup failed: {exc}")
        finally:
            _SEMANTIC_CACHE_WARMED = True

    threading.Thread(target=_warm, daemon=True).start()


_warm_semantic_cache_async()

GRAPHDB_SPARQL_ENDPOINT = os.getenv(
    "GRAPHDB_SPARQL_ENDPOINT", SEMANTIC_SPARQL_ENDPOINT
)
GRAPHDB_LUCENE_CONNECTOR = os.getenv("GRAPHDB_LUCENE_CONNECTOR", "").strip()
SPARQL_QUERY_TIMEOUT = int(os.getenv("SPARQL_QUERY_TIMEOUT", "45"))
SPARQL_QUERY_MAX_RETRIES = int(os.getenv("SPARQL_QUERY_MAX_RETRIES", "3"))
KNOWLEDGE_GRAPH_MAX_LIMIT = int(os.getenv("KNOWLEDGE_GRAPH_MAX_LIMIT", "30"))
KNOWLEDGE_GRAPH_CACHE_TTL = float(os.getenv("KNOWLEDGE_GRAPH_CACHE_TTL", "30"))
KNOWLEDGE_GRAPH_CACHE_VERSION = os.getenv("KNOWLEDGE_GRAPH_CACHE_VERSION", "1")
SEARCH_ABSTRACT_SNIPPET_CHARS = int(os.getenv("SEARCH_ABSTRACT_SNIPPET_CHARS", "150"))
MIN_SEARCH_TERM_LENGTH = int(os.getenv("SEARCH_MIN_CHARS", "3"))
_KG_CACHE: Dict[Tuple, Tuple[float, Dict[str, Any]]] = {}
_KG_CACHE_LOCK = Lock()

ERCT_PREFIX = "https://erct.adaptcentre.com/ontology#"
EX_PREFIX = "https://interdev.adaptcentre.com/id/"
SKOS_PREFIX = "http://www.w3.org/2004/02/skos/core#"
DCTERMS_PREFIX = "http://purl.org/dc/terms/"

CONDITION_SEQUENCE: List[Tuple[str, str]] = [
    ("C0", "none"),
    ("C1", "chat"),
    ("C2", "chat-sources"),
]

FILTER_NS1_MAP = {
    "Abstract": "erct:Abstract",
    "Authors": "erct:Authors",
    "Sector": "(erct:Sector|erct:hasSector/(erct:hasName|skos:prefLabel))",
    "Title": "(erct:hasName|erct:Title)",
    "Keywords": "erct:Keywords",
    "Language": "erct:Language",
    "Sub_sector": "erct:Sub-sector",
    "Sub-sector": "erct:Sub-sector",
    "Evaluation_design": "erct:Evaluation_design",
    "Equity_focus": "erct:Equity_focus",
    "Program_funding_agency": "(erct:Program_funding_agency|erct:Research_funding_agency)",
    "Implementation_agency": "erct:Implementation_agency",
    "CRS_Voluntary_DAC_Code": "erct:CRS_Voluntary_DAC_Code",
    "Unit_of_observation": "erct:Unit_of_observation",
}
SUMMARY_TRIAL_PREDICATES = [
    "erct:Abstract",
    "erct:hasAbstract",
    "erct:Authors",
    "erct:Evaluation_design",
    "erct:Implementation_agency",
    "erct:Keywords",
    "erct:Language",
    "erct:Open_Access",
    "erct:Project_name",
    "erct:Sector",
    "erct:Sub-sector",
    "erct:Title",
    "erct:hasName",
    "erct:Unit_of_observation",
    "erct:Program_funding_agency",
    "erct:Research_funding_agency",
    "erct:Ethics_Approval",
    "erct:State%2FProvince_name",
    "gn:countryCode",
    "erct:hasPublicationInfo",
]

FULL_TRIAL_PREDICATES = sorted(
    set(
        SUMMARY_TRIAL_PREDICATES
        + [
            "erct:Additional_Dataset_Information",
            "erct:Countries",
            "erct:CRS_Voluntary_DAC_Code",
            "erct:Equity_dimension",
            "erct:Mixed_method",
            "erct:Pre-Registration",
            "erct:Primary_Dataset_Availability",
            "erct:Primary_Dataset_Format",
            "erct:Protocol_Pre-Analysis_Plan",
            "erct:Secondary_Dataset_Name",
            "gn:lat",
            "gn:long",
            "gn:name",
            "gn:alternateName",
            "gn:population",
            "erct:hasCountry",
            "erct:hasExternalClassification",
            "erct:hasOutcome",
            "erct:hasMethod",
            "erct:hasPublicationInfo",
            "erct:hasSector",
        ]
    )
)


def _format_predicate_for_values(predicate: str) -> str:
    """Convert known predicates into SPARQL-safe VALUES tokens."""
    if not predicate:
        return predicate
    if predicate.startswith("<") or predicate.startswith("?"):
        return predicate
    if ":" not in predicate:
        return predicate
    prefix, local = predicate.split(":", 1)
    if "%" in local:
        if prefix == "ex":
            return f"<{EX_PREFIX}{local}>"
        if prefix == "gn":
            return f"<http://www.geonames.org/ontology#{local}>"
        if prefix == "erct":
            return f"<{ERCT_PREFIX}{local}>"
    return predicate


def _build_predicate_values_clause(predicates: List[str]) -> str:
    if not predicates:
        return ""
    formatted_predicates = [
        _format_predicate_for_values(predicate) for predicate in predicates
    ]
    joined_predicates = " ".join(formatted_predicates)
    return f"VALUES ?p {{ {joined_predicates} }}\n"


def _build_text_search_filter(escaped_search: str) -> str:
    return f"""
    FILTER (
        EXISTS {{
            ?s (erct:hasName|erct:Title) ?titleSearch .
            FILTER(CONTAINS(LCASE(?titleSearch), "{escaped_search}"))
        }} ||
        EXISTS {{
            ?s erct:Keywords ?keywordsSearch .
            FILTER(CONTAINS(LCASE(?keywordsSearch), "{escaped_search}"))
        }}
    )
    """


def _predicate_label_from_uri(uri: str) -> str:
    if "#" in uri:
        return uri.rsplit("#", 1)[-1]
    return uri.rstrip("/").split("/")[-1]


def _slugify_identifier(value: str, fallback: str = "item") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", (value or "").strip().lower()).strip("-")
    return cleaned or fallback


def _get_participant_name(required: bool = False) -> Tuple[str, Any]:
    participant = request.headers.get("X-Participant-Name", "").strip()
    if required and not participant:
        return "", (
            jsonify({"error": "X-Participant-Name header is required"}),
            400,
        )
    return participant, None


def _assign_condition_for_participant(participant: str) -> Dict[str, Any]:
    normalized_participant = (participant or "").strip().lower()
    if not normalized_participant:
        condition_id, chat_mode = CONDITION_SEQUENCE[0]
    else:
        digest = hashlib.sha256(normalized_participant.encode("utf-8")).hexdigest()
        condition_index = int(digest[:8], 16) % len(CONDITION_SEQUENCE)
        condition_id, chat_mode = CONDITION_SEQUENCE[condition_index]
    return {
        "conditionId": condition_id,
        "chatMode": chat_mode,
        "chatEnabled": chat_mode != "none",
        "citationsVisible": chat_mode == "chat-sources",
    }


def _graphdb_update_endpoint() -> str:
    endpoint = GRAPHDB_SPARQL_ENDPOINT.rstrip("/")
    if endpoint.endswith("/statements"):
        return endpoint
    return f"{endpoint}/statements"


def _execute_sparql_update(query: str):
    headers = {
        "Content-Type": "application/sparql-update",
        "Accept": "application/sparql-results+json",
    }
    response = requests.post(
        _graphdb_update_endpoint(),
        data=query.encode("utf-8"),
        headers=headers,
        timeout=max(5, SPARQL_QUERY_TIMEOUT),
    )
    response.raise_for_status()


def _collection_resource_curie(participant: str, collection_name: str) -> str:
    participant_slug = _slugify_identifier(participant, fallback="participant")
    collection_slug = _slugify_identifier(collection_name, fallback="collection")
    return f"ex:collection/{participant_slug}/{collection_slug}"


def _collection_resource_uri(participant: str, collection_name: str) -> str:
    participant_slug = _slugify_identifier(participant, fallback="participant")
    collection_slug = _slugify_identifier(collection_name, fallback="collection")
    return f"<{EX_PREFIX}collection/{participant_slug}/{collection_slug}>"


def _fetch_collection(participant: str, collection_name: str) -> Dict[str, Any]:
    collection_uri = _collection_resource_uri(participant, collection_name)
    escaped_participant = _escape_sparql_literal(participant)
    query = f"""
    PREFIX ex: <{EX_PREFIX}>
    PREFIX skos: <{SKOS_PREFIX}>
    PREFIX dcterms: <{DCTERMS_PREFIX}>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?name ?trial
    WHERE {{
        {collection_uri} a skos:Collection ;
                          rdfs:label ?name ;
                          dcterms:creator ?owner .
        FILTER(STR(?owner) = "{escaped_participant}")
        OPTIONAL {{ {collection_uri} skos:member ?trial . }}
    }}
    """
    try:
        results = _execute_json_sparql(query)
    except Exception as exc:
        print(f"[collections] Failed to fetch collection '{collection_name}': {exc}")
        return {}

    bindings = results.get("results", {}).get("bindings", [])
    if not bindings:
        return {}

    trial_ids: List[str] = []
    display_name = collection_name
    for binding in bindings:
        name = binding.get("name", {}).get("value")
        if name:
            display_name = name
        trial_uri = binding.get("trial", {}).get("value")
        if trial_uri:
            normalized_trial = _normalize_trial_identifier(trial_uri)
            if normalized_trial and normalized_trial not in trial_ids:
                trial_ids.append(normalized_trial)

    return {
        "name": display_name,
        "trialIds": trial_ids,
        "id": _collection_resource_curie(participant, display_name),
    }


def _fetch_collections_for_participant(participant: str) -> List[Dict[str, Any]]:
    escaped_participant = _escape_sparql_literal(participant)
    query = f"""
    PREFIX ex: <{EX_PREFIX}>
    PREFIX skos: <{SKOS_PREFIX}>
    PREFIX dcterms: <{DCTERMS_PREFIX}>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?collection ?name ?trial
    WHERE {{
        ?collection a skos:Collection ;
                    rdfs:label ?name ;
                    dcterms:creator ?owner .
        FILTER(STR(?owner) = "{escaped_participant}")
        OPTIONAL {{ ?collection skos:member ?trial . }}
    }}
    ORDER BY LCASE(STR(?name))
    """
    try:
        results = _execute_json_sparql(query)
    except Exception as exc:
        print(f"[collections] Failed to fetch collections for participant '{participant}': {exc}")
        return []

    collections: Dict[str, Dict[str, Any]] = {}
    for binding in results.get("results", {}).get("bindings", []):
        name = binding.get("name", {}).get("value", "").strip()
        collection_uri = binding.get("collection", {}).get("value", "").strip()
        if not name:
            continue
        if name not in collections:
            normalized_collection_id = _normalize_trial_identifier(collection_uri)
            collections[name] = {
                "name": name,
                "trialIds": [],
                "id": f"ex:{normalized_collection_id}" if normalized_collection_id else "",
            }

        trial_uri = binding.get("trial", {}).get("value")
        if trial_uri:
            normalized_trial = _normalize_trial_identifier(trial_uri)
            if normalized_trial and normalized_trial not in collections[name]["trialIds"]:
                collections[name]["trialIds"].append(normalized_trial)

    ordered_collections = sorted(collections.values(), key=lambda item: item["name"].lower())
    return ordered_collections


def _upsert_collection_resource(participant: str, collection_name: str):
    collection_uri = _collection_resource_uri(participant, collection_name)
    escaped_name = _escape_sparql_literal(collection_name)
    escaped_participant = _escape_sparql_literal(participant)
    created_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    query = f"""
    PREFIX skos: <{SKOS_PREFIX}>
    PREFIX dcterms: <{DCTERMS_PREFIX}>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    INSERT {{
        {collection_uri} a skos:Collection ;
                         rdfs:label "{escaped_name}" ;
                         dcterms:creator "{escaped_participant}" ;
                         dcterms:created "{created_at}"^^xsd:dateTime .
    }}
    WHERE {{
        FILTER NOT EXISTS {{ {collection_uri} a skos:Collection . }}
    }}
    """
    _execute_sparql_update(query)


NORMALIZED_FIELD_ALIASES = {
    "hasName": "Title",
    "hasTitle": "Title",
    "Sub-sector": "Sub_sector",
    "Pre-Registration": "Pre_Registration",
    "Protocol_Pre-Analysis_Plan": "Protocol_Pre_Analysis_Plan",
    "State%2FProvince_name": "State_Province_name",
}


def log_submission(model_name, content_submitted, participant=None):
    # Ensure the logs folder exists
    logs_folder = "logs"
    if not os.path.exists(logs_folder):
        os.makedirs(logs_folder)
    
    # Create a timestamp in ISO format
    timestamp = datetime.now().isoformat()
    log_data = {
        "model": model_name,
        "timestamp": timestamp,
        "content_submitted": content_submitted,
    }
    if participant:
        log_data["participant"] = participant
    
    # Replace colons in timestamp for filename compatibility
    safe_timestamp = timestamp.replace(":", "-")
    participant_suffix = ""
    if participant:
        safe_participant = re.sub(r"[^A-Za-z0-9_-]+", "_", participant).strip("_")
        if not safe_participant:
            safe_participant = "participant"
        participant_suffix = f"_{safe_participant}"
    filename = os.path.join(
        logs_folder, f"{model_name}{participant_suffix}_{safe_timestamp}.json"
    )

    try:
        with open(filename, "w") as f:
            json.dump(log_data, f, indent=2)
    except Exception as exc:
        print(f"Failed to persist submission log {filename}: {exc}")


def log_event(event_type: str, data: Dict, participant: str = None):
    logs_folder = "logs"
    if not os.path.exists(logs_folder):
        os.makedirs(logs_folder)

    timestamp = datetime.now().isoformat()
    safe_date = timestamp.split("T")[0].replace(":", "-")
    safe_participant = "anonymous"
    if participant:
        safe_participant = re.sub(r"[^A-Za-z0-9_-]+", "_", participant).strip("_") or "participant"

    filename = os.path.join(
        logs_folder, f"events_{safe_participant}_{safe_date}.jsonl"
    )
    record = {
        "timestamp": timestamp,
        "eventType": event_type,
        "participant": participant,
        "data": data,
    }
    try:
        with open(filename, "a") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as exc:
        print(f"Failed to persist event log: {exc}")


@main.route('/participant_condition', methods=['GET'])
def participant_condition():
    participant, error_response = _get_participant_name(required=True)
    if error_response:
        return error_response
    assignment = _assign_condition_for_participant(participant)
    return jsonify({
        "participant": participant,
        **assignment,
    })


@main.route('/collections', methods=['GET'])
def list_collections():
    participant, error_response = _get_participant_name(required=True)
    if error_response:
        return error_response
    collections = _fetch_collections_for_participant(participant)
    return jsonify({"count": len(collections), "results": collections})


@main.route('/collections', methods=['POST'])
def create_collection():
    participant, error_response = _get_participant_name(required=True)
    if error_response:
        return error_response
    body = request.get_json(force=True, silent=True) or {}
    collection_name = str(body.get("name", "")).strip()
    if not collection_name:
        return jsonify({"error": "Collection name is required"}), 400

    try:
        _upsert_collection_resource(participant, collection_name)
    except Exception as exc:
        return jsonify({"error": "Failed to create collection", "details": str(exc)}), 500

    collection = _fetch_collection(participant, collection_name)
    if not collection:
        collection = {
            "name": collection_name,
            "trialIds": [],
            "id": _collection_resource_curie(participant, collection_name),
        }
    return jsonify({"collection": collection}), 201


@main.route('/collections/<path:collection_name>/trials', methods=['POST'])
def add_trial_to_collection(collection_name: str):
    participant, error_response = _get_participant_name(required=True)
    if error_response:
        return error_response
    body = request.get_json(force=True, silent=True) or {}
    raw_trial_id = body.get("trialId")
    normalized_trial_id = _normalize_trial_identifier(raw_trial_id)
    if not normalized_trial_id:
        return jsonify({"error": "trialId is required"}), 400

    collection_name = str(collection_name or "").strip()
    if not collection_name:
        return jsonify({"error": "collection_name is required"}), 400

    try:
        _upsert_collection_resource(participant, collection_name)
        collection_uri = _collection_resource_uri(participant, collection_name)
        trial_curie = _convert_to_trial_curie(normalized_trial_id)
        if not trial_curie:
            return jsonify({"error": "Invalid trialId"}), 400
        query = f"""
        PREFIX skos: <{SKOS_PREFIX}>
        INSERT DATA {{
            {collection_uri} skos:member {trial_curie} .
        }}
        """
        _execute_sparql_update(query)
    except Exception as exc:
        return jsonify({"error": "Failed to add trial to collection", "details": str(exc)}), 500

    collection = _fetch_collection(participant, collection_name)
    return jsonify({"collection": collection})


@main.route('/collections/<path:collection_name>/trials/<path:trial_id>', methods=['DELETE'])
def remove_trial_from_collection(collection_name: str, trial_id: str):
    participant, error_response = _get_participant_name(required=True)
    if error_response:
        return error_response
    collection_name = str(collection_name or "").strip()
    if not collection_name:
        return jsonify({"error": "collection_name is required"}), 400

    normalized_trial_id = _normalize_trial_identifier(trial_id)
    if not normalized_trial_id:
        return jsonify({"error": "trialId is required"}), 400

    try:
        collection_uri = _collection_resource_uri(participant, collection_name)
        trial_curie = _convert_to_trial_curie(normalized_trial_id)
        if not trial_curie:
            return jsonify({"error": "Invalid trialId"}), 400
        query = f"""
        PREFIX skos: <{SKOS_PREFIX}>
        DELETE DATA {{
            {collection_uri} skos:member {trial_curie} .
        }}
        """
        _execute_sparql_update(query)
    except Exception as exc:
        return jsonify({"error": "Failed to remove trial from collection", "details": str(exc)}), 500

    collection = _fetch_collection(participant, collection_name)
    if not collection:
        return jsonify({
            "collection": {
                "name": collection_name,
                "trialIds": [],
                "id": _collection_resource_curie(participant, collection_name),
            }
        })
    return jsonify({"collection": collection})


@main.route('/parse_rdf', methods=['POST'])
def parse_rdf():
    try:
        # Get RDF data from the request body
        rdf_data = request.json.get('rdf', '')
        print("Raw RDF data:", rdf_data)
        if not rdf_data:
            return jsonify({'error': 'No RDF data provided'}), 400

        # Use regex to extract content between ```turtle and ```
        match = re.search(r"```turtle\s*(.*?)\s*```", rdf_data, re.DOTALL)
        if match:
            rdf_content = match.group(1)
        else:
            # If not found, fall back to removing triple backticks
            rdf_content = rdf_data.strip().strip('```').strip()
        
        print("Cleaned RDF content:", rdf_content)

        # Parse RDF data using rdflib
        graph = Graph()
        graph.parse(data=rdf_content, format='turtle')
        print("Graph has %d statements." % len(graph))

        # Mapping of predicates to user-friendly names
        key_map = {
            f"{ERCT_PREFIX}Abstract": "Abstract",
            f"{ERCT_PREFIX}Authors": "Authors",
            f"{ERCT_PREFIX}Title": "Title",
            f"{ERCT_PREFIX}hasName": "Title",
            f"{ERCT_PREFIX}Sector": "Sector",
            f"{ERCT_PREFIX}Primary_Dataset_Availability": "Primary_Dataset_Availability",
            f"{ERCT_PREFIX}Open_Access": "Open_Access",
            f"{ERCT_PREFIX}Sub-sector": "Sub_sector",
            f"{ERCT_PREFIX}Program_funding_agency": "Program_funding_agency",
            f"{ERCT_PREFIX}Evaluation_design": "Evaluation_design",
            f"{ERCT_PREFIX}Language": "Language",
            f"{ERCT_PREFIX}Equity_focus": "Equity_focus",
            f"{ERCT_PREFIX}CRS_Voluntary_DAC_Code": "CRS_Voluntary_DAC_Code",
            f"{ERCT_PREFIX}Project_name": "Project_name",
            f"{ERCT_PREFIX}Protocol_Pre-Analysis_Plan": "Protocol_Pre_Analysis_Plan",
            f"{ERCT_PREFIX}Unit_of_observation": "Unit_of_observation",
            f"{ERCT_PREFIX}Keywords": "Keywords",
            f"{ERCT_PREFIX}Ethics_Approval": "Ethics_Approval",
            f"{ERCT_PREFIX}Pre-Registration": "Pre_Registration",
            f"{ERCT_PREFIX}DOI": "DOI",
            f"{ERCT_PREFIX}Received_date": "Received_date",
            f"{ERCT_PREFIX}Revised_date": "Revised_date",
            f"{ERCT_PREFIX}Accepted_date": "Accepted_date",
            "http://www.geonames.org/ontology#countryCode": "countryCode",
            "http://www.geonames.org/ontology#lat": "latitude",
            "http://www.geonames.org/ontology#long": "longitude",
            "http://www.geonames.org/ontology#name": "countryName",
            "http://www.geonames.org/ontology#population": "population",
            f"{ERCT_PREFIX}hasOutcome": "Outcomes",
            f"{ERCT_PREFIX}hasMethod": "Methodology",
            "http://www.semanticweb.org/ERCT#hasOutcome": "Outcomes",
            "http://www.semanticweb.org/ERCT#hasMethod": "Methodology",
        }

        trial_data = {}

        # Extract main trial subject
        trial_subjects = []
        for trial_type_uri in (
            f"{ERCT_PREFIX}RandomisedControlledTrial",
            "http://www.semanticweb.org/ERCT#RandomisedControlledTrial",
        ):
            trial_subjects.extend(graph.subjects(RDF.type, URIRef(trial_type_uri)))
        if not trial_subjects:
            return jsonify({'error': 'No subjects of type RandomisedControlledTrial found'}), 404
        main_subject = trial_subjects[0]

        # General trial data extraction
        for predicate, obj in graph.predicate_objects(main_subject):
            pred_str = str(predicate)
            key = key_map.get(pred_str, _predicate_label_from_uri(pred_str))
            value = str(obj)

            if key in trial_data:
                if not isinstance(trial_data[key], list):
                    trial_data[key] = [trial_data[key]]
                trial_data[key].append(value)
            else:
                trial_data[key] = value

        # Extract Outcome details
        outcome_texts = []
        for outcome_type_uri in (
            f"{ERCT_PREFIX}Outcome",
            "http://www.semanticweb.org/ERCT#Outcome",
        ):
            for outcome in graph.subjects(RDF.type, URIRef(outcome_type_uri)):
                for predicate, obj in graph.predicate_objects(outcome):
                    pred_str = str(predicate)
                    if pred_str.endswith('hasType'):
                        outcome_texts.append(str(obj))
        if outcome_texts:
            trial_data['Outcomes'] = '; '.join(outcome_texts)

        # Extract Methodology details
        methodology_texts = []
        for method_type_uri in (
            f"{ERCT_PREFIX}Method",
            "http://www.semanticweb.org/ERCT#Method",
        ):
            for method in graph.subjects(RDF.type, URIRef(method_type_uri)):
                for predicate, obj in graph.predicate_objects(method):
                    pred_str = str(predicate)
                    if pred_str.endswith('hasExperimentalDesignType'):
                        methodology_texts.append(str(obj))
        if methodology_texts:
            trial_data['Methodology'] = '; '.join(methodology_texts)

        print("Extracted trial data:", trial_data)
        return jsonify(trial_data)

    except Exception as e:
        error_message = f"Failed to parse RDF: {str(e)}\n{traceback.format_exc()}"
        print(error_message)
        return jsonify({'error': error_message}), 500


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _escape_sparql_literal(value: str) -> str:
    """Escape special characters for safe insertion into SPARQL string literals."""
    if value is None:
        return ""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    escaped = escaped.replace("\n", "\\n").replace("\r", "\\r")
    return escaped

def process_with_gpt(extracted_text, participant=None):
    response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {
        "role": "system",
        "content": [
            {
                "type": "text",
                "text": "@prefix ercgt: <http://www.semanticweb.org/ERCT#> .\n@prefix gn: <http://www.geonames.org/ontology#> .\n@prefix ns1: <http://example.org/people/> .\n@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n\nns1:ffe40635-8c29-4afc-8bda-7044b312fa16 a ercgt:RandomisedControlledTrial ;\n    ns1:Abstract \"Background: Improved complementary feeding is cited as a critical factor for reducing stunting. Consumption of meats has been advocated, but its efficacy in low-resource settings has not been tested. Objective: The objective was to test the hypothesis that daily intake of 30 to 45 g meat from 6 to 18 mo of age would result in greater linear growth velocity and improved micronutrient status in comparison with an equicaloric multimicronutrient-fortified cereal. Design: This was a cluster randomized efficacy trial conducted in the Democratic Republic of Congo, Zambia, Guatemala, and Pakistan. Individual daily portions of study foods and education messages to enhance complementary feeding were delivered to participants. Blood tests were obtained at trial completion. Results: A total of 532 (86.1%) and 530 (85.8%) participants from the meat and cereal arms, respectively, completed the study. Linear growth velocity did not differ between treatment groups: 1.00 (95% CI: 0.99, 1.02) and 1.02 (95% CI: 1.00, 1.04) cm/mo for the meat and cereal groups, respectively (P = 0.39). From baseline to 18 mo, stunting [length-for-age z score (LAZ) <−2.0] rates increased from ∼33% to nearly 50%. Years of maternal education and maternal height were positively associated with linear growth velocity (P = 0.0006 and 0.003, respectively); LAZ at 6 mo was negatively associated (P < 0.0001). Anemia rates did not differ by group; iron deficiency was significantly lower in the cereal group. Conclusion: The high rate of stunting at baseline and the lack of effect of either the meat or multiple micronutrient-fortified cereal intervention to reverse its progression argue for multifaceted interventions beginning in the pre- and early postnatal periods. This trial was registered at clinicaltrials.gov as NCT01084109.\" ;\n    ns1:Authors \"Krebs, Nancy F.; Mazariegos, Manolo; Chomba, Elwyn; Sami, Neelofar; Pasha, Omrana; Tshefu, Antoinette; Carlo, Waldemar A.; Goldenberg, Robert L.; Bose, Carl L.; Wright, Linda L.; Koso-Thomas, Marion; Goco, Norman; Kindem, Mark; Mcclure, Elizabeth M.; Westcott, Jamie; Garces, Ana; Lokangaka, Adrien; Manasyan, Albert; Imenda, Edna; Hartwell, Tyler D.; Hambidge, Michael K.\" ;\n    ns1:CRS_Voluntary_DAC_Code \"Basic nutrition\" ;\n    ns1:Countries \"Congo, Dem. Rep., Zambia\" ;\n    ns1:Equity_focus \"Does not address gender or equity\" ;\n    ns1:Ethics_Approval \"Yes\" ;\n    ns1:Evaluation_design \"Experimental\" ;\n    ns1:Keywords \"Nutrition, Meet, Child Health, Multimicronutrient-Fortified Cereal, Stunting, food systems and nutrition\" ;\n    ns1:Language \" English\" ;\n    ns1:Mixed_method \"No\" ;\n    ns1:Open_Access \" yes\" ;\n    ns1:Pre-Registration \"No\" ;\n    ns1:Primary_Dataset_Availability \"No\" ;\n    ns1:Program_funding_agency \"National Institutes Of Health (NIH) (Government agency), National Institutes Of Health (NIH) (Government agency)\" ;\n    ns1:Protocol_Pre-Analysis_Plan \"No\" ;\n    ns1:Research_funding_agency \"National Institutes Of Health (NIH) (Academic institution), National Institutes Of Health (NIH) (Academic institution)\" ;\n    ns1:Sector \"Health\" ;\n    ns1:Sub-sector \"Health\" ;\n    ns1:Title \"Randomized Controlled Trial Of Meat Compared With Multimicronutrient-Fortified Cereal In Infants And Toddlers With High Stunting Rates In Diverse Settings\" ;\n    ns1:Unit_of_observation \"Individual\" ;\n    gn:alternateName \"Abya Yala\",\n        \"America meridionale\",\n        \"Amerika Selatan\",\n        \"Ameryka Południowa\",\n        \"Amerîkaya Başûr\",\n        \"Amèrica del Sud\",\n        \"América do Sul\",\n        \"De America\",\n        \"Dienvidamerika\",\n        \"Dél-Amerika\",\n        \"Etelä-Amerikka\",\n        \"Güney Amerika\",\n        \"Hego-Amerika\",\n        \"Jižní Amerika\",\n        \"Južna Amerika\",\n        \"Lulli-Amerihkká\",\n        \"Meiriceá Theas\",\n        \"Nam Mỹ\",\n        \"Pietų Amerika\",\n        \"Sudameriko\",\n        \"Suður-Ameríka\",\n        \"Sydamerika\",\n        \"Sør-Amerika\",\n        \"Zuid-Amerika\",\n        \"Νότια Αμερική\",\n        \"Південна Америка\",\n        \"Южна Америка\",\n        \"Южная Америка\",\n        \"אמריקה הדרומית\",\n        \"أمريكا الجنوبية\",\n        \"दक्षिणी अमरीका\",\n        \"อเมริกาใต้\",\n        \"南アメリカ\",\n        \"南美洲\" ;\n    gn:countryCode \"GT\" ;\n    gn:lat \"-14.60485\" ;\n    gn:long \"-57.65625\" ;\n    gn:name \"South America\" ;\n    gn:officialName \"Amérique du Sud\",\n        \"Južná Amerika\",\n        \"Lõuna-Ameerika\",\n        \"South America\",\n        \"Südamerika\",\n        \"남아메리카\" ;\n    gn:population \"385742554\" ;\n    gn:seeAlso \"Latin America and Caribbean\" ;\n    gn:shortName \"Sudamérica\" ;\n    ercgt:hasExternalClassification ns1:50e35d90-cf9f-457d-b370-43e8c0a64327,\n        ns1:87f744ae-b334-4bcf-a391-1b9f985aad6b,\n        ns1:c7c0bb20-ac39-4c5a-ab88-d84b730d2f1d,\n        \"Basic Health\",\n        \"Good Health and Well-being\" ;\n    ercgt:hasMethod ns1:e5acf605-f50a-466f-9a2f-5ca213fc5e52 ;\n    ercgt:hasOutcome ns1:e2e60a49-50d2-43ba-80e3-5c813813ee72 ;\n    ercgt:hasPublicationInfo ns1:84c9e863-9fd5-4ef0-8781-5886ed30067b .\n\nns1:ffe59c64-bda9-4046-ad2d-7fc036363abe a ercgt:Researcher ;\n    ercgt:hasAffiliation \"NaN\"^^xsd:double ;\n    ercgt:hasName \"Shao, Yuchen\" .\n\nns1:ffe703a4-7d2b-449c-87ec-816b5e2b7255 a ercgt:Researcher ;\n    ercgt:hasAffiliation \"Goverment of china (Government agency)\" ;\n    ercgt:hasName \"Zhang, Hongyong\" .\n\nns1:ffe91738-944a-4276-9aa8-0bc3e302d161 a ercgt:Researcher ;\n    ercgt:hasAffiliation \"Government Of Indonesia (Government agency)\" ;\n    ercgt:hasName \"Khasan, Ahmad Fatikhul\" .\n\nns1:ffe9f8ec-000f-4542-aa08-ae3a16ac6336 a ercgt:Researcher ;\n    ercgt:hasAffiliation \"NaN\"^^xsd:double ;\n    ercgt:hasName \"Nguti, Rosemary\" .\n\nns1:ffea0972-ac1b-44fe-9dab-4c2dddcd5383 a ercgt:Researcher ;\n    ercgt:hasAffiliation \"Agricultural Research Center (Government agency), National Research Center in Egypt. (Government agency)\" ;\n    ercgt:hasName \"Hussien, Hanan A.\" .\n\nns1:ffeab504-0e8b-4017-bb5c-84706687efa9 a ercgt:Researcher ;\n    ercgt:hasAffiliation \"NaN\"^^xsd:double ;\n    ercgt:hasName \"Alcides, de Jesus Padilla\" .\n\nns1:ffebb3bb-26dc-4a61-94f6-22dcbebeab5a a ercgt:Researcher ;\n    ercgt:hasAffiliation \"NaN\"^^xsd:double ;\n    ercgt:hasName \"Knerr, Beatrice\" .\n\nns1:e2e60a49-50d2-43ba-80e3-5c813813ee72 a ercgt:Outcome ;\n    ercgt:hasType \" Nutrient supplementation\"^^xsd:string .\n\nns1:2a9fa8a2-9119-40c3-b8cf-3178eda383fb a ercgt:Outcome ;\n    ercgt:hasType \" Conditional Cash Transfers (CCTs)\"^^xsd:string .\n\nns1:340e2f7b-bfd9-4a7f-8c8f-e3edcb3af6ca a ercgt:ExternalClassification ;\n    ercgt:hasUNSustainableGoal \"No Poverty\"^^xsd:string .\n\nns1:c61fce5d-1f79-4122-a002-93f43ae5946e a ercgt:ExternalClassification ;\n    ercgt:hasUNSustainableGoal \"Zero Hunger\"^^xsd:string .\n\nns1:d0f389ea-8d8a-46ea-bef3-e5ef33e25d0f a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Banking & Financial Services\"^^xsd:string .\n\nns1:e27fe64d-a630-48f0-a52d-65570dfaf307 a ercgt:Method ;\n    ercgt:hasExperimentalDesignType \"Regression discontinuity design\" .\n\nns1:8e1a75dd-6e5b-47d9-a709-024b8907afef a ercgt:Outcome ;\n    ercgt:hasType \" Environmental regulation\"^^xsd:string .\n\nns1:77893bf7-52f0-4237-8d67-d7d3d8f95a9a a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"General Environment Protection\"^^xsd:string .\n\nns1:d86d5e35-4223-454a-9d14-1482ba2a6c79 a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"General environmental protection\"^^xsd:string .\n\nns1:905b03ad-3bd8-4257-8304-0a0f2d380c3a a ercgt:ExternalClassification ;\n    ercgt:hasUNSustainableGoal \"Decent Work and Economic Growth\"^^xsd:string .\n\nns1:4f8a328f-0474-4513-9b3a-98fe2afa1e57 a ercgt:ExternalClassification ;\n    ercgt:hasUNSustainableGoal \"Quality Education\"^^xsd:string .\n\nns1:cc64fcc0-dd93-4122-b010-f83fd6e6cf73 a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Government & Civil Society - General\"^^xsd:string .\n\nns1:572f1e67-7c91-4917-864c-80ca065211d8 a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Government and civil society\"^^xsd:string .\n\nns1:128ebe91-745e-4010-948c-c93a8393a3cf a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Population policies/programmes and reproductive health\"^^xsd:string .\n\nns1:7629a814-55df-437a-9b75-235de783f4e1 a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Population Policies/Programmes & Reproductive Health\"^^xsd:string .\n\nns1:8d31f133-97b7-4557-9684-cc3d74686eb0 a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Education\"^^xsd:string .\n\nns1:dcd3a6a0-900f-4a21-af4b-d86825ee7a51 a ercgt:Method ;\n    ercgt:hasExperimentalDesignType \"Instrumental variable estimation\" .\n\nns1:0a243d28-baef-45a1-9359-b01f7c5fc157 a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Other Social Infrastructure & Services\"^^xsd:string .\n\nns1:a52063f7-3989-46b7-ad7a-e05f4305e834 a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Other social infrastructure and services\"^^xsd:string .\n\nns1:58714834-9586-43ce-97be-4f73840d194f a ercgt:PublicationInfo ;\n    ercgt:hasAbstract \"This paper studies a field experiment among energy-intensive Indian manufacturing plants that offered energy consulting to raise energy productivity, the amount plants can produce with each unit of energy. Treatment plants, after two years and relative to the control, run longer hours, demand more skilled labor and use 9.5 percent more electricity (standard error 7.3 percent). I assume that the treatment acted only through energy productivity to estimate the plant production function. The model estimates imply that energy complements skill and capital and that energy demand therefore responds more strongly to a productivity shock when plants can adjust these inputs.\"^^xsd:string ;\n    ercgt:hasDOI \" No DOI\"^^xsd:string ;\n    ercgt:hasTitle \"Energy Productivity And Energy Demand Experimental Evidence From Indian Manufacturing Plants\"^^xsd:string .\n\nns1:88edcfe4-cb43-4024-9871-f6cfd716b420 a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Agriculture\"^^xsd:string .\n\nns1:626b3ff9-3221-4067-a6bc-ec1bfa753a62 a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Agriculture, Forestry, Fishing\"^^xsd:string .\n\nns1:87f744ae-b334-4bcf-a391-1b9f985aad6b a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Basic Health\"^^xsd:string .\n\nns1:0aa4e689-2001-4f03-a83d-33522000a9c5 a ercgt:Method ;\n    ercgt:hasExperimentalDesignType \"Statistical matching\" .\n\nns1:c7c0bb20-ac39-4c5a-ab88-d84b730d2f1d a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Health\"^^xsd:string .\n\nns1:50e35d90-cf9f-457d-b370-43e8c0a64327 a ercgt:ExternalClassification ;\n    ercgt:hasUNSustainableGoal \"Good Health and Well-being\"^^xsd:string .\n\nns1:8534b6f2-7af9-43ad-913a-ef45a8439d00 a ercgt:Method ;\n    ercgt:hasExperimentalDesignType \"Fixed effects (incl. DiD)\" .\n\nns1:e5acf605-f50a-466f-9a2f-5ca213fc5e52 a ercgt:Method ;\n    ercgt:hasExperimentalDesignType \"Randomised controlled trial\" .\n\n\nns1:14e6e2cb-b8cf-40fd-87b1-7cca82c3dba6 a ercgt:RandomisedControlledTrial ;\n    ns1:Abstract \"Evidence of the impact of water, sanitation, and hygiene (WASH) in schools (WinS) interventions on pupil absence and health is mixed. Few WinS evaluations rigorously report on output and outcome measures that allow for comparisons of effectiveness between interventions to be made, or for an understanding of why programs succeed. The Water, Sanitation, and Hygiene for Health and Education in Laotian Primary Schools (WASH HELPS) study was a randomized controlled trial designed to measure the impact of the United Nations Children's Fund (UNICEF) Laos WinS project on child health and education. We also measured the sustainability of intervention outputs and outcomes, and analyzed the effectiveness of group hygiene activities on behavior change and habit formation. Here, we present the design and intermediate results from this study. We found the WinS project improved the WASH environment in intervention schools; 87.8% of schools received the intervention per design. School-level adherence to outputs was lower; on average, schools met 61.4% of adherence-related criteria. The WinS project produced positive changes in pupils' school WASH behaviors, specifically increasing toilet use and daily group handwashing. Daily group hygiene activities are effective strategies to improve school WASH behaviors, but a complementary strategy needs to be concurrently promoted for effective and sustained individual handwashing practice at critical times.\" ;\n    ns1:Authors \"Anna Chard; Matthew Freeman\" ;\n    ns1:CRS_Voluntary_DAC_Code \"Basic drinking water supply and basic sanitation\" ;\n    ns1:Equity_focus \"Does not address gender or equity\" ;\n    ns1:Ethics_Approval \"Yes\" ;\n    ns1:Evaluation_design \"Experimental\" ;\n    ns1:Implementation_agency \"United Nations Children's Fund (UNICEF) (International aid agency), Government Of Laos (Government agency)\" ;\n    ns1:Keywords \"Health Behaviour, randomized controlled trials, behaviour, schools, water, human behaviour, sanitation, hygiene\" ;\n    ns1:Language \" English\" ;\n    ns1:Mixed_method \"No\" ;\n    ns1:Open_Access \" yes\" ;\n    ns1:Pre-Registration \"Yes\" ;\n    ns1:Primary_Dataset_Availability \"Not applicable\" ;\n    ns1:Program_funding_agency \"United Nations Children's Fund (UNICEF) (International aid agency), Department of Foreign Affairs and Trade (DFAT) (Government agency), European Union (EU) (International aid agency)\" ;\n    ns1:Project_name \"WASH in schools (WinS) program\" ;\n    ns1:Protocol_Pre-Analysis_Plan \"No\" ;\n    ns1:Research_funding_agency \"United Nations Children's Fund (UNICEF) (International aid agency)\" ;\n    ns1:Sector \"Water, sanitation, and waste management\" ;\n    ns1:Sub-sector \"Sanitation\" ;\n    ns1:Title \"Design, Intervention Fidelity, and Behavioral Outcomes of a School-Based Water, Sanitation, and Hygiene Cluster-Randomized Trial in Laos\" ;\n    ns1:Unit_of_observation \"Cohort\" ;\n    gn:alternateName \"Duyun East Railway Station\",\n        \"Gare de Duyun\",\n        \"都匀东站\" ;\n    gn:countryCode \"CN\",\n        \"Lao PDR\" ;\n    gn:lat \"26.23546\" ;\n    gn:long \"107.51047\" ;\n    gn:name \"Duyun East Railway Station\" ;\n    gn:seeAlso \"East Asia and Pacific\" ;\n    ercgt:hasExternalClassification ns1:37882166-21ae-42c8-bbe0-cb20b5dd54c5,\n        ns1:3e66e2b3-3357-4f62-86e2-bf62935362df,\n        ns1:f539a05a-3c23-4598-86ba-8087e43cc883,\n        \"Clean Water and Sanitation\",\n        \"Water Supply & Sanitation\" ;\n    ercgt:hasMethod ns1:e5acf605-f50a-466f-9a2f-5ca213fc5e52,\n        ns1:ed060afa-e71e-4097-9f1e-1aa7ccb64846 ;\n    ercgt:hasOutcome ns1:bb672d84-1b2e-462e-ae9c-c93cca9b3f55 ;\n    ercgt:hasPublicationInfo ns1:01ca07a4-b686-4eb5-b62c-8915b2e8b6a3 .\n\nns1:001781dc-95e9-4daa-805c-96e3bcc300cd a ercgt:Researcher ;\n    ercgt:hasAffiliation \"United Nations Children's Fund (UNICEF) (International aid agency), Government Of Laos (Government agency)\" ;\n    ercgt:hasName \"Anna Chard\" .\n\nns1:718363c7-380e-4640-99d9-ff9050eb5489 a ercgt:Researcher ;\n    ercgt:hasAffiliation \"United Nations Children's Fund (UNICEF) (International aid agency), Government Of Laos (Government agency)\" ;\n    ercgt:hasName \"Matthew Freeman\" .\n\nns1:e5acf605-f50a-466f-9a2f-5ca213fc5e52 a ercgt:Method ;\n    ercgt:hasExperimentalDesignType \"Randomised controlled trial\" .\n\nns1:bb672d84-1b2e-462e-ae9c-c93cca9b3f55 a ercgt:Outcome ;\n    ercgt:hasType \" Sanitation hardware for child care\"^^xsd:string .\n\nI'm going to upload an academic paper. Using the same RDF formatting and schema as above, I want you cateogrise it for me. Where unique identifiers are used, you may create your own.\n Please provide the RDF between backticks, for example ```turtle <RDF content>```"
            }
        ]
        },
            {
        "role": "user",
        "content": [
            {
            "type": "text",
            "text": extracted_text
            }
        ]
        },
    ],
        temperature=1,
        max_tokens=2048,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        response_format={
            "type": "text"
        }
    )

    log_submission("gpt4o", response.choices[0].message.content, participant=participant)

    return response.choices[0].message.content

def process_with_google_gemini(extracted_text, max_retries=5, participant=None):
    """Process the extracted text using Google Gemini API."""
    system_content = (
        "@prefix ercgt: <http://www.semanticweb.org/ERCT#> .\n@prefix gn: <http://www.geonames.org/ontology#> .\n@prefix ns1: <http://example.org/people/> .\n@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n\nns1:ffe40635-8c29-4afc-8bda-7044b312fa16 a ercgt:RandomisedControlledTrial ;\n    ns1:Abstract \"Background: Improved complementary feeding is cited as a critical factor for reducing stunting. Consumption of meats has been advocated, but its efficacy in low-resource settings has not been tested. Objective: The objective was to test the hypothesis that daily intake of 30 to 45 g meat from 6 to 18 mo of age would result in greater linear growth velocity and improved micronutrient status in comparison with an equicaloric multimicronutrient-fortified cereal. Design: This was a cluster randomized efficacy trial conducted in the Democratic Republic of Congo, Zambia, Guatemala, and Pakistan. Individual daily portions of study foods and education messages to enhance complementary feeding were delivered to participants. Blood tests were obtained at trial completion. Results: A total of 532 (86.1%) and 530 (85.8%) participants from the meat and cereal arms, respectively, completed the study. Linear growth velocity did not differ between treatment groups: 1.00 (95% CI: 0.99, 1.02) and 1.02 (95% CI: 1.00, 1.04) cm/mo for the meat and cereal groups, respectively (P = 0.39). From baseline to 18 mo, stunting [length-for-age z score (LAZ) <−2.0] rates increased from ∼33% to nearly 50%. Years of maternal education and maternal height were positively associated with linear growth velocity (P = 0.0006 and 0.003, respectively); LAZ at 6 mo was negatively associated (P < 0.0001). Anemia rates did not differ by group; iron deficiency was significantly lower in the cereal group. Conclusion: The high rate of stunting at baseline and the lack of effect of either the meat or multiple micronutrient-fortified cereal intervention to reverse its progression argue for multifaceted interventions beginning in the pre- and early postnatal periods. This trial was registered at clinicaltrials.gov as NCT01084109.\" ;\n    ns1:Authors \"Krebs, Nancy F.; Mazariegos, Manolo; Chomba, Elwyn; Sami, Neelofar; Pasha, Omrana; Tshefu, Antoinette; Carlo, Waldemar A.; Goldenberg, Robert L.; Bose, Carl L.; Wright, Linda L.; Koso-Thomas, Marion; Goco, Norman; Kindem, Mark; Mcclure, Elizabeth M.; Westcott, Jamie; Garces, Ana; Lokangaka, Adrien; Manasyan, Albert; Imenda, Edna; Hartwell, Tyler D.; Hambidge, Michael K.\" ;\n    ns1:CRS_Voluntary_DAC_Code \"Basic nutrition\" ;\n    ns1:Countries \"Congo, Dem. Rep., Zambia\" ;\n    ns1:Equity_focus \"Does not address gender or equity\" ;\n    ns1:Ethics_Approval \"Yes\" ;\n    ns1:Evaluation_design \"Experimental\" ;\n    ns1:Keywords \"Nutrition, Meet, Child Health, Multimicronutrient-Fortified Cereal, Stunting, food systems and nutrition\" ;\n    ns1:Language \" English\" ;\n    ns1:Mixed_method \"No\" ;\n    ns1:Open_Access \" yes\" ;\n    ns1:Pre-Registration \"No\" ;\n    ns1:Primary_Dataset_Availability \"No\" ;\n    ns1:Program_funding_agency \"National Institutes Of Health (NIH) (Government agency), National Institutes Of Health (NIH) (Government agency)\" ;\n    ns1:Protocol_Pre-Analysis_Plan \"No\" ;\n    ns1:Research_funding_agency \"National Institutes Of Health (NIH) (Academic institution), National Institutes Of Health (NIH) (Academic institution)\" ;\n    ns1:Sector \"Health\" ;\n    ns1:Sub-sector \"Health\" ;\n    ns1:Title \"Randomized Controlled Trial Of Meat Compared With Multimicronutrient-Fortified Cereal In Infants And Toddlers With High Stunting Rates In Diverse Settings\" ;\n    ns1:Unit_of_observation \"Individual\" ;\n    gn:alternateName \"Abya Yala\",\n        \"America meridionale\",\n        \"Amerika Selatan\",\n        \"Ameryka Południowa\",\n        \"Amerîkaya Başûr\",\n        \"Amèrica del Sud\",\n        \"América do Sul\",\n        \"De America\",\n        \"Dienvidamerika\",\n        \"Dél-Amerika\",\n        \"Etelä-Amerikka\",\n        \"Güney Amerika\",\n        \"Hego-Amerika\",\n        \"Jižní Amerika\",\n        \"Južna Amerika\",\n        \"Lulli-Amerihkká\",\n        \"Meiriceá Theas\",\n        \"Nam Mỹ\",\n        \"Pietų Amerika\",\n        \"Sudameriko\",\n        \"Suður-Ameríka\",\n        \"Sydamerika\",\n        \"Sør-Amerika\",\n        \"Zuid-Amerika\",\n        \"Νότια Αμερική\",\n        \"Південна Америка\",\n        \"Южна Америка\",\n        \"Южная Америка\",\n        \"אמריקה הדרומית\",\n        \"أمريكا الجنوبية\",\n        \"दक्षिणी अमरीका\",\n        \"อเมริกาใต้\",\n        \"南アメリカ\",\n        \"南美洲\" ;\n    gn:countryCode \"GT\" ;\n    gn:lat \"-14.60485\" ;\n    gn:long \"-57.65625\" ;\n    gn:name \"South America\" ;\n    gn:officialName \"Amérique du Sud\",\n        \"Južná Amerika\",\n        \"Lõuna-Ameerika\",\n        \"South America\",\n        \"Südamerika\",\n        \"남아메리카\" ;\n    gn:population \"385742554\" ;\n    gn:seeAlso \"Latin America and Caribbean\" ;\n    gn:shortName \"Sudamérica\" ;\n    ercgt:hasExternalClassification ns1:50e35d90-cf9f-457d-b370-43e8c0a64327,\n        ns1:87f744ae-b334-4bcf-a391-1b9f985aad6b,\n        ns1:c7c0bb20-ac39-4c5a-ab88-d84b730d2f1d,\n        \"Basic Health\",\n        \"Good Health and Well-being\" ;\n    ercgt:hasMethod ns1:e5acf605-f50a-466f-9a2f-5ca213fc5e52 ;\n    ercgt:hasOutcome ns1:e2e60a49-50d2-43ba-80e3-5c813813ee72 ;\n    ercgt:hasPublicationInfo ns1:84c9e863-9fd5-4ef0-8781-5886ed30067b .\n\nns1:ffe59c64-bda9-4046-ad2d-7fc036363abe a ercgt:Researcher ;\n    ercgt:hasAffiliation \"NaN\"^^xsd:double ;\n    ercgt:hasName \"Shao, Yuchen\" .\n\nns1:ffe703a4-7d2b-449c-87ec-816b5e2b7255 a ercgt:Researcher ;\n    ercgt:hasAffiliation \"Goverment of china (Government agency)\" ;\n    ercgt:hasName \"Zhang, Hongyong\" .\n\nns1:ffe91738-944a-4276-9aa8-0bc3e302d161 a ercgt:Researcher ;\n    ercgt:hasAffiliation \"Government Of Indonesia (Government agency)\" ;\n    ercgt:hasName \"Khasan, Ahmad Fatikhul\" .\n\nns1:ffe9f8ec-000f-4542-aa08-ae3a16ac6336 a ercgt:Researcher ;\n    ercgt:hasAffiliation \"NaN\"^^xsd:double ;\n    ercgt:hasName \"Nguti, Rosemary\" .\n\nns1:ffea0972-ac1b-44fe-9dab-4c2dddcd5383 a ercgt:Researcher ;\n    ercgt:hasAffiliation \"Agricultural Research Center (Government agency), National Research Center in Egypt. (Government agency)\" ;\n    ercgt:hasName \"Hussien, Hanan A.\" .\n\nns1:ffeab504-0e8b-4017-bb5c-84706687efa9 a ercgt:Researcher ;\n    ercgt:hasAffiliation \"NaN\"^^xsd:double ;\n    ercgt:hasName \"Alcides, de Jesus Padilla\" .\n\nns1:ffebb3bb-26dc-4a61-94f6-22dcbebeab5a a ercgt:Researcher ;\n    ercgt:hasAffiliation \"NaN\"^^xsd:double ;\n    ercgt:hasName \"Knerr, Beatrice\" .\n\nns1:e2e60a49-50d2-43ba-80e3-5c813813ee72 a ercgt:Outcome ;\n    ercgt:hasType \" Nutrient supplementation\"^^xsd:string .\n\nns1:2a9fa8a2-9119-40c3-b8cf-3178eda383fb a ercgt:Outcome ;\n    ercgt:hasType \" Conditional Cash Transfers (CCTs)\"^^xsd:string .\n\nns1:340e2f7b-bfd9-4a7f-8c8f-e3edcb3af6ca a ercgt:ExternalClassification ;\n    ercgt:hasUNSustainableGoal \"No Poverty\"^^xsd:string .\n\nns1:c61fce5d-1f79-4122-a002-93f43ae5946e a ercgt:ExternalClassification ;\n    ercgt:hasUNSustainableGoal \"Zero Hunger\"^^xsd:string .\n\nns1:d0f389ea-8d8a-46ea-bef3-e5ef33e25d0f a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Banking & Financial Services\"^^xsd:string .\n\nns1:e27fe64d-a630-48f0-a52d-65570dfaf307 a ercgt:Method ;\n    ercgt:hasExperimentalDesignType \"Regression discontinuity design\" .\n\nns1:8e1a75dd-6e5b-47d9-a709-024b8907afef a ercgt:Outcome ;\n    ercgt:hasType \" Environmental regulation\"^^xsd:string .\n\nns1:77893bf7-52f0-4237-8d67-d7d3d8f95a9a a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"General Environment Protection\"^^xsd:string .\n\nns1:d86d5e35-4223-454a-9d14-1482ba2a6c79 a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"General environmental protection\"^^xsd:string .\n\nns1:905b03ad-3bd8-4257-8304-0a0f2d380c3a a ercgt:ExternalClassification ;\n    ercgt:hasUNSustainableGoal \"Decent Work and Economic Growth\"^^xsd:string .\n\nns1:4f8a328f-0474-4513-9b3a-98fe2afa1e57 a ercgt:ExternalClassification ;\n    ercgt:hasUNSustainableGoal \"Quality Education\"^^xsd:string .\n\nns1:cc64fcc0-dd93-4122-b010-f83fd6e6cf73 a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Government & Civil Society - General\"^^xsd:string .\n\nns1:572f1e67-7c91-4917-864c-80ca065211d8 a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Government and civil society\"^^xsd:string .\n\nns1:128ebe91-745e-4010-948c-c93a8393a3cf a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Population policies/programmes and reproductive health\"^^xsd:string .\n\nns1:7629a814-55df-437a-9b75-235de783f4e1 a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Population Policies/Programmes & Reproductive Health\"^^xsd:string .\n\nns1:8d31f133-97b7-4557-9684-cc3d74686eb0 a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Education\"^^xsd:string .\n\nns1:dcd3a6a0-900f-4a21-af4b-d86825ee7a51 a ercgt:Method ;\n    ercgt:hasExperimentalDesignType \"Instrumental variable estimation\" .\n\nns1:0a243d28-baef-45a1-9359-b01f7c5fc157 a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Other Social Infrastructure & Services\"^^xsd:string .\n\nns1:a52063f7-3989-46b7-ad7a-e05f4305e834 a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Other social infrastructure and services\"^^xsd:string .\n\nns1:58714834-9586-43ce-97be-4f73840d194f a ercgt:PublicationInfo ;\n    ercgt:hasAbstract \"This paper studies a field experiment among energy-intensive Indian manufacturing plants that offered energy consulting to raise energy productivity, the amount plants can produce with each unit of energy. Treatment plants, after two years and relative to the control, run longer hours, demand more skilled labor and use 9.5 percent more electricity (standard error 7.3 percent). I assume that the treatment acted only through energy productivity to estimate the plant production function. The model estimates imply that energy complements skill and capital and that energy demand therefore responds more strongly to a productivity shock when plants can adjust these inputs.\"^^xsd:string ;\n    ercgt:hasDOI \" No DOI\"^^xsd:string ;\n    ercgt:hasTitle \"Energy Productivity And Energy Demand Experimental Evidence From Indian Manufacturing Plants\"^^xsd:string .\n\nns1:88edcfe4-cb43-4024-9871-f6cfd716b420 a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Agriculture\"^^xsd:string .\n\nns1:626b3ff9-3221-4067-a6bc-ec1bfa753a62 a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Agriculture, Forestry, Fishing\"^^xsd:string .\n\nns1:87f744ae-b334-4bcf-a391-1b9f985aad6b a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Basic Health\"^^xsd:string .\n\nns1:0aa4e689-2001-4f03-a83d-33522000a9c5 a ercgt:Method ;\n    ercgt:hasExperimentalDesignType \"Statistical matching\" .\n\nns1:c7c0bb20-ac39-4c5a-ab88-d84b730d2f1d a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Health\"^^xsd:string .\n\nns1:50e35d90-cf9f-457d-b370-43e8c0a64327 a ercgt:ExternalClassification ;\n    ercgt:hasUNSustainableGoal \"Good Health and Well-being\"^^xsd:string .\n\nns1:8534b6f2-7af9-43ad-913a-ef45a8439d00 a ercgt:Method ;\n    ercgt:hasExperimentalDesignType \"Fixed effects (incl. DiD)\" .\n\nns1:e5acf605-f50a-466f-9a2f-5ca213fc5e52 a ercgt:Method ;\n    ercgt:hasExperimentalDesignType \"Randomised controlled trial\" .\n\n\nns1:14e6e2cb-b8cf-40fd-87b1-7cca82c3dba6 a ercgt:RandomisedControlledTrial ;\n    ns1:Abstract \"Evidence of the impact of water, sanitation, and hygiene (WASH) in schools (WinS) interventions on pupil absence and health is mixed. Few WinS evaluations rigorously report on output and outcome measures that allow for comparisons of effectiveness between interventions to be made, or for an understanding of why programs succeed. The Water, Sanitation, and Hygiene for Health and Education in Laotian Primary Schools (WASH HELPS) study was a randomized controlled trial designed to measure the impact of the United Nations Children's Fund (UNICEF) Laos WinS project on child health and education. We also measured the sustainability of intervention outputs and outcomes, and analyzed the effectiveness of group hygiene activities on behavior change and habit formation. Here, we present the design and intermediate results from this study. We found the WinS project improved the WASH environment in intervention schools; 87.8% of schools received the intervention per design. School-level adherence to outputs was lower; on average, schools met 61.4% of adherence-related criteria. The WinS project produced positive changes in pupils' school WASH behaviors, specifically increasing toilet use and daily group handwashing. Daily group hygiene activities are effective strategies to improve school WASH behaviors, but a complementary strategy needs to be concurrently promoted for effective and sustained individual handwashing practice at critical times.\" ;\n    ns1:Authors \"Anna Chard; Matthew Freeman\" ;\n    ns1:CRS_Voluntary_DAC_Code \"Basic drinking water supply and basic sanitation\" ;\n    ns1:Equity_focus \"Does not address gender or equity\" ;\n    ns1:Ethics_Approval \"Yes\" ;\n    ns1:Evaluation_design \"Experimental\" ;\n    ns1:Implementation_agency \"United Nations Children's Fund (UNICEF) (International aid agency), Government Of Laos (Government agency)\" ;\n    ns1:Keywords \"Health Behaviour, randomized controlled trials, behaviour, schools, water, human behaviour, sanitation, hygiene\" ;\n    ns1:Language \" English\" ;\n    ns1:Mixed_method \"No\" ;\n    ns1:Open_Access \" yes\" ;\n    ns1:Pre-Registration \"Yes\" ;\n    ns1:Primary_Dataset_Availability \"Not applicable\" ;\n    ns1:Program_funding_agency \"United Nations Children's Fund (UNICEF) (International aid agency), Department of Foreign Affairs and Trade (DFAT) (Government agency), European Union (EU) (International aid agency)\" ;\n    ns1:Project_name \"WASH in schools (WinS) program\" ;\n    ns1:Protocol_Pre-Analysis_Plan \"No\" ;\n    ns1:Research_funding_agency \"United Nations Children's Fund (UNICEF) (International aid agency)\" ;\n    ns1:Sector \"Water, sanitation, and waste management\" ;\n    ns1:Sub-sector \"Sanitation\" ;\n    ns1:Title \"Design, Intervention Fidelity, and Behavioral Outcomes of a School-Based Water, Sanitation, and Hygiene Cluster-Randomized Trial in Laos\" ;\n    ns1:Unit_of_observation \"Cohort\" ;\n    gn:alternateName \"Duyun East Railway Station\",\n        \"Gare de Duyun\",\n        \"都匀东站\" ;\n    gn:countryCode \"CN\",\n        \"Lao PDR\" ;\n    gn:lat \"26.23546\" ;\n    gn:long \"107.51047\" ;\n    gn:name \"Duyun East Railway Station\" ;\n    gn:seeAlso \"East Asia and Pacific\" ;\n    ercgt:hasExternalClassification ns1:37882166-21ae-42c8-bbe0-cb20b5dd54c5,\n        ns1:3e66e2b3-3357-4f62-86e2-bf62935362df,\n        ns1:f539a05a-3c23-4598-86ba-8087e43cc883,\n        \"Clean Water and Sanitation\",\n        \"Water Supply & Sanitation\" ;\n    ercgt:hasMethod ns1:e5acf605-f50a-466f-9a2f-5ca213fc5e52,\n        ns1:ed060afa-e71e-4097-9f1e-1aa7ccb64846 ;\n    ercgt:hasOutcome ns1:bb672d84-1b2e-462e-ae9c-c93cca9b3f55 ;\n    ercgt:hasPublicationInfo ns1:01ca07a4-b686-4eb5-b62c-8915b2e8b6a3 .\n\nns1:001781dc-95e9-4daa-805c-96e3bcc300cd a ercgt:Researcher ;\n    ercgt:hasAffiliation \"United Nations Children's Fund (UNICEF) (International aid agency), Government Of Laos (Government agency)\" ;\n    ercgt:hasName \"Anna Chard\" .\n\nns1:718363c7-380e-4640-99d9-ff9050eb5489 a ercgt:Researcher ;\n    ercgt:hasAffiliation \"United Nations Children's Fund (UNICEF) (International aid agency), Government Of Laos (Government agency)\" ;\n    ercgt:hasName \"Matthew Freeman\" .\n\nns1:e5acf605-f50a-466f-9a2f-5ca213fc5e52 a ercgt:Method ;\n    ercgt:hasExperimentalDesignType \"Randomised controlled trial\" .\n\nns1:bb672d84-1b2e-462e-ae9c-c93cca9b3f55 a ercgt:Outcome ;\n    ercgt:hasType \" Sanitation hardware for child care\"^^xsd:string .\n\n"
    )

    user_prompt = (
        "I'm going to upload an academic paper. Using the same RDF formatting and schema as above, I want you cateogrise it for me. Where unique identifiers are used, you may create your own.\n"
        f"{extracted_text}"
    )

    wait_time = 5  # Initial wait time in seconds

    for attempt in range(max_retries):
        try:
            # Send the structured prompt to Google Gemini
            response = genai.generate_text(
                model="gemini-1.5-pro",  # Specify the Gemini model
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=1,
                max_output_tokens=2048,
                top_p=1,
            )
            log_submission("gemini-1.5", response.result, participant=participant)

            return response.result  # Return the generated text from Gemini

        except Exception as e:
            if "rate limit" in str(e).lower() or "429" in str(e):
                print(f"Rate limit hit. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                wait_time *= 2  # Exponential backoff
            else:
                print(f"Error calling Google Gemini API: {e}")
                break  # Stop retrying for other errors

    print("Failed to process after maximum retries.")
    return None


@main.route('/log_event', methods=['POST'])
def receive_event():
    participant = request.headers.get("X-Participant-Name", "").strip() or None
    body = request.get_json(force=True, silent=True) or {}
    event_type = body.get("eventType")
    event_data = body.get("data", {})
    if not event_type:
        return jsonify({"error": "eventType is required"}), 400
    if not isinstance(event_data, dict):
        return jsonify({"error": "data must be an object"}), 400
    log_event(event_type, event_data, participant=participant)
    return jsonify({"status": "ok"})


def process_with_claude(extracted_text, max_retries=5, participant=None):
    """Process the extracted text using Anthropic Claude API."""
    system_content = (
        "@prefix ercgt: <http://www.semanticweb.org/ERCT#> .\n@prefix gn: <http://www.geonames.org/ontology#> .\n@prefix ns1: <http://example.org/people/> .\n@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n\nns1:ffe40635-8c29-4afc-8bda-7044b312fa16 a ercgt:RandomisedControlledTrial ;\n    ns1:Abstract \"Background: Improved complementary feeding is cited as a critical factor for reducing stunting. Consumption of meats has been advocated, but its efficacy in low-resource settings has not been tested. Objective: The objective was to test the hypothesis that daily intake of 30 to 45 g meat from 6 to 18 mo of age would result in greater linear growth velocity and improved micronutrient status in comparison with an equicaloric multimicronutrient-fortified cereal. Design: This was a cluster randomized efficacy trial conducted in the Democratic Republic of Congo, Zambia, Guatemala, and Pakistan. Individual daily portions of study foods and education messages to enhance complementary feeding were delivered to participants. Blood tests were obtained at trial completion. Results: A total of 532 (86.1%) and 530 (85.8%) participants from the meat and cereal arms, respectively, completed the study. Linear growth velocity did not differ between treatment groups: 1.00 (95% CI: 0.99, 1.02) and 1.02 (95% CI: 1.00, 1.04) cm/mo for the meat and cereal groups, respectively (P = 0.39). From baseline to 18 mo, stunting [length-for-age z score (LAZ) <−2.0] rates increased from ∼33% to nearly 50%. Years of maternal education and maternal height were positively associated with linear growth velocity (P = 0.0006 and 0.003, respectively); LAZ at 6 mo was negatively associated (P < 0.0001). Anemia rates did not differ by group; iron deficiency was significantly lower in the cereal group. Conclusion: The high rate of stunting at baseline and the lack of effect of either the meat or multiple micronutrient-fortified cereal intervention to reverse its progression argue for multifaceted interventions beginning in the pre- and early postnatal periods. This trial was registered at clinicaltrials.gov as NCT01084109.\" ;\n    ns1:Authors \"Krebs, Nancy F.; Mazariegos, Manolo; Chomba, Elwyn; Sami, Neelofar; Pasha, Omrana; Tshefu, Antoinette; Carlo, Waldemar A.; Goldenberg, Robert L.; Bose, Carl L.; Wright, Linda L.; Koso-Thomas, Marion; Goco, Norman; Kindem, Mark; Mcclure, Elizabeth M.; Westcott, Jamie; Garces, Ana; Lokangaka, Adrien; Manasyan, Albert; Imenda, Edna; Hartwell, Tyler D.; Hambidge, Michael K.\" ;\n    ns1:CRS_Voluntary_DAC_Code \"Basic nutrition\" ;\n    ns1:Countries \"Congo, Dem. Rep., Zambia\" ;\n    ns1:Equity_focus \"Does not address gender or equity\" ;\n    ns1:Ethics_Approval \"Yes\" ;\n    ns1:Evaluation_design \"Experimental\" ;\n    ns1:Keywords \"Nutrition, Meet, Child Health, Multimicronutrient-Fortified Cereal, Stunting, food systems and nutrition\" ;\n    ns1:Language \" English\" ;\n    ns1:Mixed_method \"No\" ;\n    ns1:Open_Access \" yes\" ;\n    ns1:Pre-Registration \"No\" ;\n    ns1:Primary_Dataset_Availability \"No\" ;\n    ns1:Program_funding_agency \"National Institutes Of Health (NIH) (Government agency), National Institutes Of Health (NIH) (Government agency)\" ;\n    ns1:Protocol_Pre-Analysis_Plan \"No\" ;\n    ns1:Research_funding_agency \"National Institutes Of Health (NIH) (Academic institution), National Institutes Of Health (NIH) (Academic institution)\" ;\n    ns1:Sector \"Health\" ;\n    ns1:Sub-sector \"Health\" ;\n    ns1:Title \"Randomized Controlled Trial Of Meat Compared With Multimicronutrient-Fortified Cereal In Infants And Toddlers With High Stunting Rates In Diverse Settings\" ;\n    ns1:Unit_of_observation \"Individual\" ;\n    gn:alternateName \"Abya Yala\",\n        \"America meridionale\",\n        \"Amerika Selatan\",\n        \"Ameryka Południowa\",\n        \"Amerîkaya Başûr\",\n        \"Amèrica del Sud\",\n        \"América do Sul\",\n        \"De America\",\n        \"Dienvidamerika\",\n        \"Dél-Amerika\",\n        \"Etelä-Amerikka\",\n        \"Güney Amerika\",\n        \"Hego-Amerika\",\n        \"Jižní Amerika\",\n        \"Južna Amerika\",\n        \"Lulli-Amerihkká\",\n        \"Meiriceá Theas\",\n        \"Nam Mỹ\",\n        \"Pietų Amerika\",\n        \"Sudameriko\",\n        \"Suður-Ameríka\",\n        \"Sydamerika\",\n        \"Sør-Amerika\",\n        \"Zuid-Amerika\",\n        \"Νότια Αμερική\",\n        \"Південна Америка\",\n        \"Южна Америка\",\n        \"Южная Америка\",\n        \"אמריקה הדרומית\",\n        \"أمريكا الجنوبية\",\n        \"दक्षिणी अमरीका\",\n        \"อเมริกาใต้\",\n        \"南アメリカ\",\n        \"南美洲\" ;\n    gn:countryCode \"GT\" ;\n    gn:lat \"-14.60485\" ;\n    gn:long \"-57.65625\" ;\n    gn:name \"South America\" ;\n    gn:officialName \"Amérique du Sud\",\n        \"Južná Amerika\",\n        \"Lõuna-Ameerika\",\n        \"South America\",\n        \"Südamerika\",\n        \"남아메리카\" ;\n    gn:population \"385742554\" ;\n    gn:seeAlso \"Latin America and Caribbean\" ;\n    gn:shortName \"Sudamérica\" ;\n    ercgt:hasExternalClassification ns1:50e35d90-cf9f-457d-b370-43e8c0a64327,\n        ns1:87f744ae-b334-4bcf-a391-1b9f985aad6b,\n        ns1:c7c0bb20-ac39-4c5a-ab88-d84b730d2f1d,\n        \"Basic Health\",\n        \"Good Health and Well-being\" ;\n    ercgt:hasMethod ns1:e5acf605-f50a-466f-9a2f-5ca213fc5e52 ;\n    ercgt:hasOutcome ns1:e2e60a49-50d2-43ba-80e3-5c813813ee72 ;\n    ercgt:hasPublicationInfo ns1:84c9e863-9fd5-4ef0-8781-5886ed30067b .\n\nns1:ffe59c64-bda9-4046-ad2d-7fc036363abe a ercgt:Researcher ;\n    ercgt:hasAffiliation \"NaN\"^^xsd:double ;\n    ercgt:hasName \"Shao, Yuchen\" .\n\nns1:ffe703a4-7d2b-449c-87ec-816b5e2b7255 a ercgt:Researcher ;\n    ercgt:hasAffiliation \"Goverment of china (Government agency)\" ;\n    ercgt:hasName \"Zhang, Hongyong\" .\n\nns1:ffe91738-944a-4276-9aa8-0bc3e302d161 a ercgt:Researcher ;\n    ercgt:hasAffiliation \"Government Of Indonesia (Government agency)\" ;\n    ercgt:hasName \"Khasan, Ahmad Fatikhul\" .\n\nns1:ffe9f8ec-000f-4542-aa08-ae3a16ac6336 a ercgt:Researcher ;\n    ercgt:hasAffiliation \"NaN\"^^xsd:double ;\n    ercgt:hasName \"Nguti, Rosemary\" .\n\nns1:ffea0972-ac1b-44fe-9dab-4c2dddcd5383 a ercgt:Researcher ;\n    ercgt:hasAffiliation \"Agricultural Research Center (Government agency), National Research Center in Egypt. (Government agency)\" ;\n    ercgt:hasName \"Hussien, Hanan A.\" .\n\nns1:ffeab504-0e8b-4017-bb5c-84706687efa9 a ercgt:Researcher ;\n    ercgt:hasAffiliation \"NaN\"^^xsd:double ;\n    ercgt:hasName \"Alcides, de Jesus Padilla\" .\n\nns1:ffebb3bb-26dc-4a61-94f6-22dcbebeab5a a ercgt:Researcher ;\n    ercgt:hasAffiliation \"NaN\"^^xsd:double ;\n    ercgt:hasName \"Knerr, Beatrice\" .\n\nns1:e2e60a49-50d2-43ba-80e3-5c813813ee72 a ercgt:Outcome ;\n    ercgt:hasType \" Nutrient supplementation\"^^xsd:string .\n\nns1:2a9fa8a2-9119-40c3-b8cf-3178eda383fb a ercgt:Outcome ;\n    ercgt:hasType \" Conditional Cash Transfers (CCTs)\"^^xsd:string .\n\nns1:340e2f7b-bfd9-4a7f-8c8f-e3edcb3af6ca a ercgt:ExternalClassification ;\n    ercgt:hasUNSustainableGoal \"No Poverty\"^^xsd:string .\n\nns1:c61fce5d-1f79-4122-a002-93f43ae5946e a ercgt:ExternalClassification ;\n    ercgt:hasUNSustainableGoal \"Zero Hunger\"^^xsd:string .\n\nns1:d0f389ea-8d8a-46ea-bef3-e5ef33e25d0f a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Banking & Financial Services\"^^xsd:string .\n\nns1:e27fe64d-a630-48f0-a52d-65570dfaf307 a ercgt:Method ;\n    ercgt:hasExperimentalDesignType \"Regression discontinuity design\" .\n\nns1:8e1a75dd-6e5b-47d9-a709-024b8907afef a ercgt:Outcome ;\n    ercgt:hasType \" Environmental regulation\"^^xsd:string .\n\nns1:77893bf7-52f0-4237-8d67-d7d3d8f95a9a a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"General Environment Protection\"^^xsd:string .\n\nns1:d86d5e35-4223-454a-9d14-1482ba2a6c79 a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"General environmental protection\"^^xsd:string .\n\nns1:905b03ad-3bd8-4257-8304-0a0f2d380c3a a ercgt:ExternalClassification ;\n    ercgt:hasUNSustainableGoal \"Decent Work and Economic Growth\"^^xsd:string .\n\nns1:4f8a328f-0474-4513-9b3a-98fe2afa1e57 a ercgt:ExternalClassification ;\n    ercgt:hasUNSustainableGoal \"Quality Education\"^^xsd:string .\n\nns1:cc64fcc0-dd93-4122-b010-f83fd6e6cf73 a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Government & Civil Society - General\"^^xsd:string .\n\nns1:572f1e67-7c91-4917-864c-80ca065211d8 a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Government and civil society\"^^xsd:string .\n\nns1:128ebe91-745e-4010-948c-c93a8393a3cf a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Population policies/programmes and reproductive health\"^^xsd:string .\n\nns1:7629a814-55df-437a-9b75-235de783f4e1 a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Population Policies/Programmes & Reproductive Health\"^^xsd:string .\n\nns1:8d31f133-97b7-4557-9684-cc3d74686eb0 a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Education\"^^xsd:string .\n\nns1:dcd3a6a0-900f-4a21-af4b-d86825ee7a51 a ercgt:Method ;\n    ercgt:hasExperimentalDesignType \"Instrumental variable estimation\" .\n\nns1:0a243d28-baef-45a1-9359-b01f7c5fc157 a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Other Social Infrastructure & Services\"^^xsd:string .\n\nns1:a52063f7-3989-46b7-ad7a-e05f4305e834 a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Other social infrastructure and services\"^^xsd:string .\n\nns1:58714834-9586-43ce-97be-4f73840d194f a ercgt:PublicationInfo ;\n    ercgt:hasAbstract \"This paper studies a field experiment among energy-intensive Indian manufacturing plants that offered energy consulting to raise energy productivity, the amount plants can produce with each unit of energy. Treatment plants, after two years and relative to the control, run longer hours, demand more skilled labor and use 9.5 percent more electricity (standard error 7.3 percent). I assume that the treatment acted only through energy productivity to estimate the plant production function. The model estimates imply that energy complements skill and capital and that energy demand therefore responds more strongly to a productivity shock when plants can adjust these inputs.\"^^xsd:string ;\n    ercgt:hasDOI \" No DOI\"^^xsd:string ;\n    ercgt:hasTitle \"Energy Productivity And Energy Demand Experimental Evidence From Indian Manufacturing Plants\"^^xsd:string .\n\nns1:88edcfe4-cb43-4024-9871-f6cfd716b420 a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Agriculture\"^^xsd:string .\n\nns1:626b3ff9-3221-4067-a6bc-ec1bfa753a62 a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Agriculture, Forestry, Fishing\"^^xsd:string .\n\nns1:87f744ae-b334-4bcf-a391-1b9f985aad6b a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Basic Health\"^^xsd:string .\n\nns1:0aa4e689-2001-4f03-a83d-33522000a9c5 a ercgt:Method ;\n    ercgt:hasExperimentalDesignType \"Statistical matching\" .\n\nns1:c7c0bb20-ac39-4c5a-ab88-d84b730d2f1d a ercgt:ExternalClassification ;\n    ercgt:hasDAC \"Health\"^^xsd:string .\n\nns1:50e35d90-cf9f-457d-b370-43e8c0a64327 a ercgt:ExternalClassification ;\n    ercgt:hasUNSustainableGoal \"Good Health and Well-being\"^^xsd:string .\n\nns1:8534b6f2-7af9-43ad-913a-ef45a8439d00 a ercgt:Method ;\n    ercgt:hasExperimentalDesignType \"Fixed effects (incl. DiD)\" .\n\nns1:e5acf605-f50a-466f-9a2f-5ca213fc5e52 a ercgt:Method ;\n    ercgt:hasExperimentalDesignType \"Randomised controlled trial\" .\n\n\nns1:14e6e2cb-b8cf-40fd-87b1-7cca82c3dba6 a ercgt:RandomisedControlledTrial ;\n    ns1:Abstract \"Evidence of the impact of water, sanitation, and hygiene (WASH) in schools (WinS) interventions on pupil absence and health is mixed. Few WinS evaluations rigorously report on output and outcome measures that allow for comparisons of effectiveness between interventions to be made, or for an understanding of why programs succeed. The Water, Sanitation, and Hygiene for Health and Education in Laotian Primary Schools (WASH HELPS) study was a randomized controlled trial designed to measure the impact of the United Nations Children's Fund (UNICEF) Laos WinS project on child health and education. We also measured the sustainability of intervention outputs and outcomes, and analyzed the effectiveness of group hygiene activities on behavior change and habit formation. Here, we present the design and intermediate results from this study. We found the WinS project improved the WASH environment in intervention schools; 87.8% of schools received the intervention per design. School-level adherence to outputs was lower; on average, schools met 61.4% of adherence-related criteria. The WinS project produced positive changes in pupils' school WASH behaviors, specifically increasing toilet use and daily group handwashing. Daily group hygiene activities are effective strategies to improve school WASH behaviors, but a complementary strategy needs to be concurrently promoted for effective and sustained individual handwashing practice at critical times.\" ;\n    ns1:Authors \"Anna Chard; Matthew Freeman\" ;\n    ns1:CRS_Voluntary_DAC_Code \"Basic drinking water supply and basic sanitation\" ;\n    ns1:Equity_focus \"Does not address gender or equity\" ;\n    ns1:Ethics_Approval \"Yes\" ;\n    ns1:Evaluation_design \"Experimental\" ;\n    ns1:Implementation_agency \"United Nations Children's Fund (UNICEF) (International aid agency), Government Of Laos (Government agency)\" ;\n    ns1:Keywords \"Health Behaviour, randomized controlled trials, behaviour, schools, water, human behaviour, sanitation, hygiene\" ;\n    ns1:Language \" English\" ;\n    ns1:Mixed_method \"No\" ;\n    ns1:Open_Access \" yes\" ;\n    ns1:Pre-Registration \"Yes\" ;\n    ns1:Primary_Dataset_Availability \"Not applicable\" ;\n    ns1:Program_funding_agency \"United Nations Children's Fund (UNICEF) (International aid agency), Department of Foreign Affairs and Trade (DFAT) (Government agency), European Union (EU) (International aid agency)\" ;\n    ns1:Project_name \"WASH in schools (WinS) program\" ;\n    ns1:Protocol_Pre-Analysis_Plan \"No\" ;\n    ns1:Research_funding_agency \"United Nations Children's Fund (UNICEF) (International aid agency)\" ;\n    ns1:Sector \"Water, sanitation, and waste management\" ;\n    ns1:Sub-sector \"Sanitation\" ;\n    ns1:Title \"Design, Intervention Fidelity, and Behavioral Outcomes of a School-Based Water, Sanitation, and Hygiene Cluster-Randomized Trial in Laos\" ;\n    ns1:Unit_of_observation \"Cohort\" ;\n    gn:alternateName \"Duyun East Railway Station\",\n        \"Gare de Duyun\",\n        \"都匀东站\" ;\n    gn:countryCode \"CN\",\n        \"Lao PDR\" ;\n    gn:lat \"26.23546\" ;\n    gn:long \"107.51047\" ;\n    gn:name \"Duyun East Railway Station\" ;\n    gn:seeAlso \"East Asia and Pacific\" ;\n    ercgt:hasExternalClassification ns1:37882166-21ae-42c8-bbe0-cb20b5dd54c5,\n        ns1:3e66e2b3-3357-4f62-86e2-bf62935362df,\n        ns1:f539a05a-3c23-4598-86ba-8087e43cc883,\n        \"Clean Water and Sanitation\",\n        \"Water Supply & Sanitation\" ;\n    ercgt:hasMethod ns1:e5acf605-f50a-466f-9a2f-5ca213fc5e52,\n        ns1:ed060afa-e71e-4097-9f1e-1aa7ccb64846 ;\n    ercgt:hasOutcome ns1:bb672d84-1b2e-462e-ae9c-c93cca9b3f55 ;\n    ercgt:hasPublicationInfo ns1:01ca07a4-b686-4eb5-b62c-8915b2e8b6a3 .\n\nns1:001781dc-95e9-4daa-805c-96e3bcc300cd a ercgt:Researcher ;\n    ercgt:hasAffiliation \"United Nations Children's Fund (UNICEF) (International aid agency), Government Of Laos (Government agency)\" ;\n    ercgt:hasName \"Anna Chard\" .\n\nns1:718363c7-380e-4640-99d9-ff9050eb5489 a ercgt:Researcher ;\n    ercgt:hasAffiliation \"United Nations Children's Fund (UNICEF) (International aid agency), Government Of Laos (Government agency)\" ;\n    ercgt:hasName \"Matthew Freeman\" .\n\nns1:e5acf605-f50a-466f-9a2f-5ca213fc5e52 a ercgt:Method ;\n    ercgt:hasExperimentalDesignType \"Randomised controlled trial\" .\n\nns1:bb672d84-1b2e-462e-ae9c-c93cca9b3f55 a ercgt:Outcome ;\n    ercgt:hasType \" Sanitation hardware for child care\"^^xsd:string .\n\n"
    )

    user_prompt = (
        "I'm going to upload an academic paper. Using the same RDF formatting and schema as above, I want you cateogrise it for me. Where unique identifiers are used, you may create your own.\n"
        f"{extracted_text}"
    )

    wait_time = 5  

    for attempt in range(max_retries):
        try:
            # Make a request to Claude API
            response = anthropicClient.completions.create(
                model="claude-3-5-sonnet-20241022",  # Specify the Claude model
                prompt=f"{anthropic.HUMAN_PROMPT}{system_content}\n{user_prompt}{anthropic.AI_PROMPT}",
                max_tokens_to_sample=2048,
                temperature=1,
            )
            log_submission("claude", response['completion'], participant=participant)

            return response['completion']  # Extract text from the response

        except anthropic.RateLimitError:
            print(f"Rate limit hit. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
            wait_time *= 2  # Exponential backoff
        except Exception as e:
            print(f"Error calling Claude API: {e}")
            break  # Exit on non-rate-limit errors

    print("Failed to process after maximum retries.")
    return None


@main.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    selected_ai = request.form.get('selected_ai', 'GPT')  # Default to GPT if not specified

    participant = request.headers.get("X-Participant-Name", "").strip() or None

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Ensure the upload folder exists
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Extract text from the uploaded PDF
        try:
            extracted_text = extract_text(filepath)
            print(extracted_text)
        except Exception as e:
            return jsonify({'error': f'Failed to extract text from PDF: {str(e)}'}), 500

        # Process the extracted text with the selected AI model
        try:
            if selected_ai == 'GPT':
                response = process_with_gpt(extracted_text, participant=participant)
            elif selected_ai == 'Google_Gemini':
                response = process_with_google_gemini(extracted_text, participant=participant)
            elif selected_ai == 'Claude_Anthropic':
                response = process_with_claude(extracted_text, participant=participant)
            else:
                return jsonify({'error': f'Unsupported AI model: {selected_ai}'}), 400

            # Return the response and source metadata for provenance recording
            return jsonify({
                "response": response,
                "sourceDocumentTitle": filename,
            })

        except Exception as e:
            return jsonify({'error': f'Failed to process AI model: {str(e)}'}), 500

    else:
        return jsonify({'error': 'File not allowed'}), 400


@main.route('/search', methods=['GET'])
def search():
    # Simulate a SPARQL search and return a fixed result
    results = ['Item 1', 'Item 2', 'Item 3']
    return jsonify({'results': results})


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def clean_trial(trial):
    cleaned_trial = {}

    for key, value in trial.items():
        clean_key = NORMALIZED_FIELD_ALIASES.get(
            _predicate_label_from_uri(key), _predicate_label_from_uri(key)
        )

        if isinstance(value, list):
            value = ", ".join(value)

        if isinstance(value, str):
            value = value.replace("\u00a0", " ").strip()  # Replace non-breaking spaces

        cleaned_trial[clean_key] = value

    if "Title" not in cleaned_trial:
        if "hasName" in cleaned_trial:
            cleaned_trial["Title"] = cleaned_trial["hasName"]
        elif "hasTitle" in cleaned_trial:
            cleaned_trial["Title"] = cleaned_trial["hasTitle"]

    if "Abstract" not in cleaned_trial and "hasAbstract" in cleaned_trial:
        cleaned_trial["Abstract"] = cleaned_trial["hasAbstract"]

    if "Sub_sector" not in cleaned_trial and "Sub-sector" in cleaned_trial:
        cleaned_trial["Sub_sector"] = cleaned_trial["Sub-sector"]

    if (
        "Program_funding_agency" not in cleaned_trial
        and "Research_funding_agency" in cleaned_trial
    ):
        cleaned_trial["Program_funding_agency"] = cleaned_trial["Research_funding_agency"]

    return cleaned_trial


def _trial_subject_to_id(subject: str) -> str:
    return _normalize_trial_identifier(subject)


def _normalize_trial_identifier(trial_id: str) -> str:
    if not trial_id:
        return ""
    candidate = str(trial_id).strip().strip("<>").strip()
    if candidate.startswith(("ns1:", "ex:")):
        candidate = candidate.split(":", 1)[-1]
    if candidate.startswith("urn:"):
        candidate = candidate.split(":")[-1]
    elif candidate.startswith("http"):
        candidate = candidate.rstrip("/").split("/")[-1]
    return candidate


def _split_multi_value_field(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        raw_values = value
    else:
        raw_values = [part.strip() for part in str(value).split(",")]
    return [entry.strip() for entry in raw_values if entry.strip()]


def _convert_bindings_to_trials(bindings: List[Dict]) -> List[Dict]:
    processed_data: Dict[str, Dict] = {}

    for result in bindings:
        subject = result["s"]["value"]
        trial_id = _trial_subject_to_id(subject)

        if subject not in processed_data:
            processed_data[subject] = {"id": trial_id}

        predicate = _predicate_label_from_uri(result["p"]["value"])
        object_value = result["o"]["value"]

        if predicate in processed_data[subject]:
            if not isinstance(processed_data[subject][predicate], list):
                processed_data[subject][predicate] = [
                    processed_data[subject][predicate]
                ]
            processed_data[subject][predicate].append(object_value)
        else:
            processed_data[subject][predicate] = object_value

    filtered_data = []
    for trial in processed_data.values():
        has_title = "Title" in trial or "hasName" in trial or "hasTitle" in trial
        has_abstract = "Abstract" in trial or "hasAbstract" in trial
        if has_title and has_abstract and "Authors" in trial:
            filtered_data.append(trial)

    return [clean_trial(trial) for trial in filtered_data]


def _fetch_sector_labels_for_trials(trial_ids: List[str]) -> Dict[str, List[str]]:
    normalized_ids = []
    for trial_id in trial_ids:
        normalized = _normalize_trial_identifier(trial_id)
        if normalized:
            normalized_ids.append(normalized)

    if not normalized_ids:
        return {}

    values_clause = " ".join([f"ex:{trial_id}" for trial_id in sorted(set(normalized_ids))])
    query = f"""
    PREFIX erct: <{ERCT_PREFIX}>
    PREFIX ex: <{EX_PREFIX}>
    PREFIX skos: <{SKOS_PREFIX}>
    SELECT ?trial ?label
    WHERE {{
        VALUES ?trial {{ {values_clause} }}
        ?trial erct:hasSector ?sectorNode .
        OPTIONAL {{ ?sectorNode skos:prefLabel ?sectorPrefLabel }}
        OPTIONAL {{ ?sectorNode erct:hasName ?sectorName }}
        BIND(COALESCE(?sectorPrefLabel, ?sectorName) AS ?label)
        FILTER(BOUND(?label))
    }}
    """
    try:
        results = _execute_json_sparql(query)
    except Exception as exc:
        print(f"[kg] Failed to fetch sector labels: {exc}")
        return {}

    labels_by_trial: Dict[str, set] = {}
    for binding in results.get("results", {}).get("bindings", []):
        trial_uri = binding.get("trial", {}).get("value")
        label = (binding.get("label", {}).get("value") or "").strip()
        trial_id = _normalize_trial_identifier(trial_uri)
        if not trial_id or not label:
            continue
        labels_by_trial.setdefault(trial_id, set()).add(label)

    return {
        trial_id: sorted(labels)
        for trial_id, labels in labels_by_trial.items()
        if labels
    }


def _enrich_trials_with_sector_labels(trials: List[Dict]) -> None:
    if not trials:
        return
    missing_ids = []
    for trial in trials:
        trial_id = _normalize_trial_identifier(trial.get("id"))
        if not trial_id:
            continue
        sector_value = str(trial.get("Sector", "")).strip()
        if not sector_value:
            missing_ids.append(trial_id)

    if not missing_ids:
        return

    labels_by_trial = _fetch_sector_labels_for_trials(missing_ids)
    if not labels_by_trial:
        return

    for trial in trials:
        trial_id = _normalize_trial_identifier(trial.get("id"))
        labels = labels_by_trial.get(trial_id)
        if labels:
            trial["Sector"] = ", ".join(labels)


def _convert_to_trial_curie(trial_id: str) -> str:
    """Best-effort conversion of various trial id formats into the ex: CURIE used in the KG."""
    if not trial_id:
        return ""
    trial_id = str(trial_id).strip()
    if not trial_id:
        return ""
    if trial_id.startswith("ex:"):
        return trial_id
    if trial_id.startswith("ns1:"):
        return f"ex:{trial_id.split(':', 1)[-1]}"
    if trial_id.startswith("urn:"):
        return f"<{trial_id}>"
    if trial_id.startswith("http"):
        fragment = trial_id.rstrip("/").split("/")[-1]
        return f"ex:{fragment}"
    if ":" in trial_id:
        return trial_id
    return f"ex:{trial_id}"


def _normalise_doi_to_url(doi: str) -> str:
    """Return a clickable URL for a DOI-like string, if possible."""
    if not doi:
        return ""
    cleaned = str(doi).strip()
    if not cleaned:
        return ""
    if cleaned.lower().startswith("http"):
        return cleaned
    cleaned = cleaned.removeprefix("doi:").strip()
    cleaned = cleaned.lstrip("/")
    if not cleaned:
        return ""
    return f"https://doi.org/{cleaned}"


def _execute_json_sparql(query: str) -> Dict:
    """Execute a SPARQL query against GraphDB with retries and timeout."""
    delay = 0.5
    last_exc = None
    attempts = max(1, SPARQL_QUERY_MAX_RETRIES)
    for attempt in range(1, attempts + 1):
        client = SPARQLWrapper(GRAPHDB_SPARQL_ENDPOINT)
        client.setReturnFormat(JSON)
        client.setMethod(POST)
        client.setTimeout(max(1, SPARQL_QUERY_TIMEOUT))
        client.setQuery(query)
        try:
            return client.query().convert()
        except IncompleteRead as exc:
            partial = getattr(exc, "partial", b"") or b""
            if partial:
                try:
                    return json.loads(partial.decode("utf-8"))
                except Exception as decode_exc:
                    last_exc = decode_exc
            else:
                last_exc = exc
        except Exception as exc:
            last_exc = exc

        if attempt < attempts:
            print(f"[kg] SPARQL attempt {attempt} failed: {last_exc}")
            time.sleep(min(delay, 5))
            delay = min(delay * 2, 10)

    raise last_exc or Exception("Unknown SPARQL execution failure")


def _build_trials_context_text(trial_ids=None, limit=None):
    """Fetch structured context and provenance data for selected trials to ground chat."""
    try:
        if not trial_ids:
            return "", [], []
        sparql = SPARQLWrapper(GRAPHDB_SPARQL_ENDPOINT)
        prefixes = """
        PREFIX erct: <https://erct.adaptcentre.com/ontology#>
        PREFIX ex: <https://interdev.adaptcentre.com/id/>
        PREFIX gn: <http://www.geonames.org/ontology#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        """
        formatted_ids = []
        for tid in trial_ids:
            curie = _convert_to_trial_curie(tid)
            if curie:
                formatted_ids.append(curie)
        if not formatted_ids:
            return "", [], []
        if limit and limit > 0:
            formatted_ids = formatted_ids[:limit]
        values_clause = "VALUES ?trial { " + " ".join(formatted_ids) + " }"
        query = f"""
        {prefixes}
        SELECT
            ?trial
            ?title
            ?abstract
            ?authors
            ?pubTitle
            ?pubAbstract
            ?doi
            ?outcomeText
            ?methodText
            ?sector
            ?country
            ?funding
        WHERE {{
            {values_clause}
            ?trial a erct:RandomisedControlledTrial .
            OPTIONAL {{ ?trial erct:hasName ?titlePrimary }}
            OPTIONAL {{ ?trial erct:Title ?titleLegacy }}
            BIND(COALESCE(?titlePrimary, ?titleLegacy) AS ?title)
            OPTIONAL {{ ?trial erct:Abstract ?abstractPrimary }}
            OPTIONAL {{ ?trial erct:hasAbstract ?abstractLegacy }}
            BIND(COALESCE(?abstractPrimary, ?abstractLegacy) AS ?abstract)
            OPTIONAL {{ ?trial erct:Authors ?authors }}
            OPTIONAL {{ ?trial erct:Sector ?sectorLiteral }}
            OPTIONAL {{
                ?trial erct:hasSector ?sectorNode .
                OPTIONAL {{ ?sectorNode skos:prefLabel ?sectorPrefLabel }}
                OPTIONAL {{ ?sectorNode erct:hasName ?sectorName }}
            }}
            BIND(COALESCE(?sectorLiteral, ?sectorPrefLabel, ?sectorName) AS ?sector)
            OPTIONAL {{ ?trial gn:countryCode ?country }}
            OPTIONAL {{ ?trial erct:Program_funding_agency ?fundingProgram }}
            OPTIONAL {{ ?trial erct:Research_funding_agency ?fundingResearch }}
            BIND(COALESCE(?fundingProgram, ?fundingResearch) AS ?funding)
            OPTIONAL {{
                ?trial erct:hasOutcome ?outcomeNode .
                OPTIONAL {{ ?outcomeNode erct:hasType ?outcomeText }}
            }}
            OPTIONAL {{
                ?trial erct:hasMethod ?methodNode .
                OPTIONAL {{ ?methodNode erct:hasExperimentalDesignType ?methodText }}
            }}
            OPTIONAL {{
                ?trial erct:hasPublicationInfo ?pubInfo .
                OPTIONAL {{ ?pubInfo erct:hasTitle ?pubTitle }}
                OPTIONAL {{ ?pubInfo erct:hasAbstract ?pubAbstract }}
                OPTIONAL {{ ?pubInfo erct:hasDOI ?doi }}
            }}
            FILTER(BOUND(?title))
        }}
        """
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()
        context_map: Dict[str, Dict] = {}
        evidence_map: Dict[Tuple[str, str, str], Dict] = {}
        order: List[str] = []
        for b in results.get("results", {}).get("bindings", []):
            title = b.get("title", {}).get("value", "").strip()
            abstract = b.get("abstract", {}).get("value", "").strip()
            authors = b.get("authors", {}).get("value", "").strip()
            pub_title = b.get("pubTitle", {}).get("value", "").strip()
            pub_abstract = b.get("pubAbstract", {}).get("value", "").strip()
            doi_raw = b.get("doi", {}).get("value", "").strip()
            doi_url = _normalise_doi_to_url(doi_raw)
            trial_uri = b.get("trial", {}).get("value")
            trial_curie = _convert_to_trial_curie(trial_uri)
            outcome_text = b.get("outcomeText", {}).get("value", "").strip()
            method_text = b.get("methodText", {}).get("value", "").strip()
            sector = b.get("sector", {}).get("value", "").strip()
            country = b.get("country", {}).get("value", "").strip()
            funding = b.get("funding", {}).get("value", "").strip()

            if not trial_curie:
                continue

            if trial_curie not in context_map:
                context_map[trial_curie] = {
                    "trialCurie": trial_curie,
                    "title": title,
                    "authors": set(),
                    "sectors": set(),
                    "countries": set(),
                    "funders": set(),
                    "methods": set(),
                    "outcomes": set(),
                    "keywords": set(),
                    "summary": "",
                }
                order.append(trial_curie)

            entry = context_map[trial_curie]
            if title and not entry.get("title"):
                entry["title"] = title
            if authors:
                entry["authors"].add(authors)
            if sector:
                entry["sectors"].add(sector)
            if country:
                entry["countries"].add(country)
            if funding:
                entry["funders"].add(funding)
            if method_text:
                entry["methods"].add(method_text)
            if outcome_text:
                entry["outcomes"].add(outcome_text)

            summary_text = pub_abstract or abstract
            if summary_text:
                summary_text = summary_text.replace("\n", " ").strip()
                entry["summary"] = summary_text

            source_key = (trial_curie, pub_title or title or entry.get("title") or "", doi_url)
            if source_key not in evidence_map:
                evidence_map[source_key] = {
                    "id": f"{trial_curie}#publication",
                    "trialId": trial_curie,
                    "trialTitle": entry.get("title") or title,
                    "authors": authors,
                    "sourceTitle": pub_title or title or entry.get("title") or "",
                    "sourceUrl": doi_url or "",
                    "doi": doi_raw,
                    "excerpt": (pub_abstract or abstract)[:1000] if (pub_abstract or abstract) else "",
                }

        if not context_map:
            return "", [], []

        lines: List[str] = []
        context_details: List[Dict] = []
        for trial_curie in order:
            entry = context_map[trial_curie]
            summary = entry.get("summary") or "No abstract available"
            snippet = summary[:800]
            authors_text = ", ".join(sorted(entry["authors"])) if entry["authors"] else "Unknown authors"
            annotations = []
            if entry["sectors"]:
                annotations.append(f"Sector: {', '.join(sorted(entry['sectors']))}")
            if entry["countries"]:
                annotations.append(f"Country code: {', '.join(sorted(entry['countries']))}")
            if entry["funders"]:
                annotations.append(f"Funding: {', '.join(sorted(entry['funders']))}")
            if entry["methods"]:
                annotations.append(f"Methodology: {', '.join(sorted(entry['methods']))}")
            if entry["outcomes"]:
                annotations.append(f"Outcomes: {', '.join(sorted(entry['outcomes']))}")
            annotation_text = ""
            if annotations:
                annotation_text = "\n  " + "\n  ".join(annotations)
            lines.append(
                f"- Title: {entry.get('title') or 'Untitled Trial'}\n  Authors: {authors_text}\n  Summary: {snippet}{annotation_text}"
            )
            context_details.append(
                {
                    "trialCurie": trial_curie,
                    "title": entry.get("title"),
                    "authors": sorted(entry["authors"]),
                    "summary": summary,
                    "sectors": sorted(entry["sectors"]),
                    "countries": sorted(entry["countries"]),
                    "funders": sorted(entry["funders"]),
                    "methods": sorted(entry["methods"]),
                    "outcomes": sorted(entry["outcomes"]),
                }
            )

        evidence: List[Dict] = []
        for (trial_curie, _, _), record in evidence_map.items():
            entry = context_map.get(trial_curie, {})
            record["trialCurie"] = trial_curie
            record["sectors"] = sorted(entry.get("sectors", []))
            record["countries"] = sorted(entry.get("countries", []))
            record["funders"] = sorted(entry.get("funders", []))
            record["methods"] = sorted(entry.get("methods", []))
            record["outcomes"] = sorted(entry.get("outcomes", []))
            evidence.append(record)

        return "\n".join(lines), evidence, context_details
    except Exception as e:
        print(f"Failed to build trials context: {e}")
        return "", [], []


@main.route('/chat', methods=['POST'])
def chat_with_llm():
    """Simple chat endpoint backed by OpenAI Chat Completions.

    Expects JSON: {
      messages: [{role: 'user'|'assistant'|'system', content: string}],
      trialIds?: ["ex:..." or id],
      filters?: object
    }
    """
    try:
        participant, error_response = _get_participant_name(required=True)
        if error_response:
            return error_response
        assignment = _assign_condition_for_participant(participant)
        if not assignment.get("chatEnabled"):
            return jsonify({
                "error": "Chat is disabled for this participant condition",
                "conditionId": assignment.get("conditionId"),
                "chatMode": assignment.get("chatMode"),
            }), 403
        citations_visible = bool(assignment.get("citationsVisible"))
        body = request.get_json(force=True, silent=False) or {}
        messages = body.get('messages', [])
        if not isinstance(messages, list) or not messages:
            return jsonify({"error": "messages must be a non-empty array"}), 400

        trial_ids = body.get('trialIds', [])
        context_text, evidence, context_details = _build_trials_context_text(trial_ids=trial_ids)

        system_preamble = (
            "You are an academic research assistant helping users discuss randomized controlled trials (RCTs). "
            "Write in a coherent, professional tone suitable for scholarly communication. "
            "When answering questions about a collection, synthesize evidence across the majority of the referenced trials "
            "rather than focusing on a single work. "
            "Use the provided context when relevant, cite specific trial titles when referring to them, and keep answers concise and accurate. "
            "If unsure, say so."
        )
        if citations_visible:
            system_preamble += " When referencing provided sources, include citations like [S1] that correspond to the source list."
        else:
            system_preamble += " Do not use inline source markers like [S1] and do not output a source list."
        if citations_visible:
            system_preamble += (
                "\n\nExample (format only):\n"
                "User: \"Recommend books on urban climate adaptation and explain why they fit.\""
                "\nSources:"
                "\n[S1] Coastal Resilience Handbook (Lee, 2019) - emphasizes heat-mitigation and flood planning."
                "\n[S2] Cities After Carbon (Patel, 2021) - focuses on policy tools and financing."
                "\nAssistant: \"Coastal Resilience Handbook is a strong fit because it directly addresses practical adaptation "
                "measures for cities facing heat and flooding, matching your focus on urban resilience [S1]. Cities After Carbon "
                "complements it by framing the policy and funding levers that make those interventions viable, providing the "
                "governance context you asked for [S2].\""
                "\nGraph: Coastal Resilience Handbook --shared_author--> Resilient Shorelines (edge note: both authored by Lee)."
            )
        else:
            system_preamble += (
                "\n\nExample (format only):\n"
                "User: \"Recommend books on urban climate adaptation and explain why they fit.\""
                "\nAssistant: \"Coastal Resilience Handbook is a strong fit because it directly addresses practical adaptation "
                "measures for cities facing heat and flooding, while Cities After Carbon complements it by explaining policy and "
                "financing levers that support those interventions.\""
            )
        if context_text:
            system_preamble += "\n\nContext trials (subset):\n" + context_text
        if evidence and citations_visible:
            source_lines = []
            system_preamble += (
                "\n\nKey ontology terms:\n"
                "- RandomisedControlledTrial: core entity representing an RCT.\n"
                "- hasOutcome: links a trial to outcome nodes (erct:hasOutcome).\n"
                "- hasMethod: links to methodology nodes (erct:hasMethod).\n"
                "- Program_funding_agency / Research_funding_agency: funding organisation.\n"
                "- Sector: primary sector classification (erct:Sector / erct:hasSector).\n"
                "- countryCode: ISO-3166 country code (gn:countryCode)."
            )
            for idx, src in enumerate(evidence, start=1):
                label = src.get("sourceTitle") or src.get("trialTitle") or "Source"
                trial_title = src.get("trialTitle")
                url = (src.get("sourceUrl") or "").strip()
                excerpt = (src.get("excerpt") or "").replace("\n", " ").strip()
                excerpt_snippet = (excerpt[:400] + "…") if len(excerpt) > 400 else excerpt
                parts = [f"[S{idx}] {label}"]
                if trial_title and trial_title != label:
                    parts.append(f"(Trial: {trial_title})")
                trial_curie = src.get("trialId") or src.get("id")
                if trial_curie:
                    parts.append(f"[{trial_curie}]")
                if url:
                    parts.append(f"<{url}>")
                if excerpt_snippet:
                    parts.append(f"Excerpt: {excerpt_snippet}")
                source_lines.append(" ".join(parts))
            system_preamble += "\n\nSources:\n" + "\n".join(source_lines)

        openai_messages = [{"role": "system", "content": system_preamble}]
        # Accept only role/content pairs, drop anything else
        for m in messages:
            role = m.get('role')
            content = m.get('content')
            if role in ("user", "assistant", "system") and isinstance(content, str):
                openai_messages.append({"role": role, "content": content})

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=openai_messages,
            temperature=0.2,
            max_tokens=800,
            top_p=1,
        )

        reply = response.choices[0].message.content
        log_submission(
            "chat-gpt-4o-mini",
            {
                "messages": messages,
                "trialIds": trial_ids,
                "reply": reply,
                "sources": evidence if citations_visible else [],
                "context": context_details,
                "condition": assignment,
            },
            participant=participant,
        )
        return jsonify({
            "reply": reply,
            "sources": evidence if citations_visible else [],
            "context": context_details,
            "condition": assignment,
        })
    except Exception as e:
        print(f"/chat error: {e}\n{traceback.format_exc()}")
        return jsonify({"error": "Failed to generate chat reply", "details": str(e)}), 500


@main.route('/download_knowledge_graph_data', methods=['GET'])
def download_knowledge_graph_data():
    from SPARQLWrapper import SPARQLWrapper, JSON  # Ensure you import CSV if needed
    sparql = SPARQLWrapper(GRAPHDB_SPARQL_ENDPOINT)
    sparql.setReturnFormat(JSON)  # Initially set to JSON to process query parameters

    # Retrieve trial IDs and filters from query parameters
    trial_ids = request.args.getlist('trialIds')
    filters = request.args.to_dict(flat=False)
    filters.pop('trialIds', None)  # Remove 'trialIds' from filters if present
    search_term = (request.args.get('search') or "").strip()
    filters.pop('search', None)

    # Get the requested download format (default is turtle)
    download_format = request.args.get('format', 'turtle').lower()

    # Define prefixes for the query
    prefixes = """
    PREFIX erct: <https://erct.adaptcentre.com/ontology#>
    PREFIX gn: <http://www.geonames.org/ontology#>
    PREFIX ex: <https://interdev.adaptcentre.com/id/>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    PREFIX lucene: <http://www.ontotext.com/connectors/lucene#>
    """

    # Build filter conditions based on supported predicates
    filter_conditions = ""
    for key, values in filters.items():
        if key in FILTER_NS1_MAP:
            predicate_uri = FILTER_NS1_MAP[key]
        elif key == 'countryCode':
            predicate_uri = "gn:countryCode"
        else:
            continue  # Skip unsupported filters

        for value in values:
            if value is None:
                continue
            raw_value = str(value).strip()
            if not raw_value:
                continue
            escaped_value = _escape_sparql_literal(raw_value)
            filter_conditions += f'?s {predicate_uri} "{escaped_value}" .\n'

    # Build VALUES clause if trial IDs are provided
    values_clause = ""
    if trial_ids:
        normalized_trial_ids = [
            _normalize_trial_identifier(trial_id) for trial_id in trial_ids if trial_id
        ]
        normalized_trial_ids = [trial_id for trial_id in normalized_trial_ids if trial_id]
        values_clause = (
            "VALUES ?s { " + " ".join([f"ex:{trial_id}" for trial_id in normalized_trial_ids]) + " } "
        )

    search_filter = ""
    if search_term and GRAPHDB_LUCENE_CONNECTOR:
        escaped_search = _escape_sparql_literal(search_term)
        search_filter = f"""
        SERVICE lucene:search {{
            ?searchHit lucene:set "{GRAPHDB_LUCENE_CONNECTOR}" ;
                       lucene:query "{escaped_search}" ;
                       lucene:entities ?s .
        }}
        """
    elif search_term:
        escaped_search = _escape_sparql_literal(search_term.lower())
        search_filter = _build_text_search_filter(escaped_search)

    if download_format == "csv":
        # Use a SELECT query for CSV output
        query = f"""
        {prefixes}
        SELECT ?s ?p ?o
        WHERE {{
            {values_clause}
            ?s a erct:RandomisedControlledTrial ;
               ?p ?o .
            {filter_conditions}
            {search_filter}
        }}
        """
        sparql.setQuery(query)
        sparql.setReturnFormat('csv')  # Request CSV format
        results = sparql.query().convert()

        response = make_response(results)
        response.headers['Content-Type'] = 'text/csv'
    else:
        # Default to Turtle format using a CONSTRUCT query
        query = f"""
        {prefixes}
        CONSTRUCT {{ ?s ?p ?o }}
        WHERE {{
            {values_clause}
            ?s a erct:RandomisedControlledTrial ;
               ?p ?o .
            {filter_conditions}
            {search_filter}
        }}
        """
        sparql.setQuery(query)
        sparql.setReturnFormat('turtle')
        results = sparql.query().convert()

        response = make_response(results)
        response.headers['Content-Type'] = 'text/turtle'
        
    return response



@main.route('/knowledge_graph_data', methods=['GET'])
def fetch_knowledge_graph_data():    
    raw_trial_ids = request.args.getlist('trialIds')  # Get multiple trialIds
    limit = request.args.get('limit', default=5, type=int)  # Fetch the limit
    if not limit or limit < 1:
        limit = 5
    if KNOWLEDGE_GRAPH_MAX_LIMIT and KNOWLEDGE_GRAPH_MAX_LIMIT > 0:
        limit = min(limit, KNOWLEDGE_GRAPH_MAX_LIMIT)

    filters = request.args.to_dict(flat=False)
    filters.pop('limit', None)  # Remove 'limit' if present in filters
    filters.pop('trialIds', None)  # Remove 'trialIds' if present in filters
    search_term = (request.args.get('search') or "").strip()
    filters.pop('search', None)
    view_mode = (request.args.get('view') or "detail").strip().lower()
    if view_mode not in ("summary", "detail"):
        view_mode = "detail"
    filters.pop('view', None)
    if search_term and len(search_term) < MIN_SEARCH_TERM_LENGTH:
        return jsonify({"count": 0, "results": []})
    normalized_trial_ids = []
    for trial_id in raw_trial_ids:
        normalized_id = _normalize_trial_identifier(trial_id)
        if normalized_id:
            normalized_trial_ids.append(normalized_id)
    predicate_list = (
        FULL_TRIAL_PREDICATES if view_mode == "detail" else SUMMARY_TRIAL_PREDICATES
    )
    predicate_clause = _build_predicate_values_clause(predicate_list)

    prefixes = """
    PREFIX erct: <https://erct.adaptcentre.com/ontology#>
    PREFIX gn: <http://www.geonames.org/ontology#>
    PREFIX ex: <https://interdev.adaptcentre.com/id/>
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    PREFIX lucene: <http://www.ontotext.com/connectors/lucene#>
    """

    filter_conditions = ""
    for key, values in filters.items():
        if key in FILTER_NS1_MAP:
            predicate_uri = FILTER_NS1_MAP[key]
        elif key == 'countryCode':
            predicate_uri = "gn:countryCode"
        else:
            continue  # Skip unsupported filters
        for value in values:
            if value is None:
                continue
            raw_value = str(value).strip()
            if not raw_value:
                continue
            escaped_value = _escape_sparql_literal(raw_value)
            filter_conditions += f'?s {predicate_uri} "{escaped_value}" .\n'

    search_filter = ""
    if search_term and GRAPHDB_LUCENE_CONNECTOR:
        escaped_search = _escape_sparql_literal(search_term)
        search_filter = f"""
        SERVICE lucene:search {{
            ?searchHit lucene:set "{GRAPHDB_LUCENE_CONNECTOR}" ;
                       lucene:query "{escaped_search}" ;
                       lucene:entities ?s .
        }}
        """
    elif search_term:
        escaped_search = _escape_sparql_literal(search_term.lower())
        search_filter = _build_text_search_filter(escaped_search)

    cache_key = (
        KNOWLEDGE_GRAPH_CACHE_VERSION,
        tuple(normalized_trial_ids),
        limit,
        tuple(sorted((key, tuple(values)) for key, values in filters.items())),
        search_term,
        view_mode,
    )

    stale_payload = None
    request_id = uuid.uuid4().hex[:8]
    timings = []
    start_time = time.perf_counter()
    now = time.time()
    if KNOWLEDGE_GRAPH_CACHE_TTL > 0:
        with _KG_CACHE_LOCK:
            cached_entry = _KG_CACHE.get(cache_key)
            if cached_entry:
                cached_ts, cached_payload = cached_entry
                age = now - cached_ts
                if age < KNOWLEDGE_GRAPH_CACHE_TTL:
                    timings.append(("cache_hit", time.perf_counter() - start_time))
                    print(f"[kg/{request_id}] timings={timings}")
                    response = make_response(jsonify(cached_payload))
                    response.headers['Access-Control-Allow-Origin'] = '*'
                    response.headers['X-Cache'] = 'hit'
                    return response
                stale_payload = cached_payload

    has_trial_ids = bool(normalized_trial_ids)
    values_clause = ""
    if has_trial_ids:
        values_clause = "VALUES ?s { " + " ".join([f"ex:{tid}" for tid in normalized_trial_ids]) + " }\n"

    sample_order = os.getenv("GRAPHDB_SAMPLE_ORDER_BY", "RAND()")
    sample_limit = int(os.getenv("GRAPHDB_SAMPLE_LIMIT", str(max(limit, 200))))

    if has_trial_ids:
        query = f"""
        {prefixes}
        SELECT ?s ?p ?o
        WHERE {{
            {values_clause}
            {predicate_clause}
            ?s a erct:RandomisedControlledTrial ;
               ?p ?o .
            {filter_conditions}
            {search_filter}
        }}
        """
    else:
        query = f"""
        {prefixes}
        SELECT ?s ?p ?o
        WHERE {{
            {{
                SELECT DISTINCT ?s
                WHERE {{
                    ?s a erct:RandomisedControlledTrial .
                    {filter_conditions}
                    {search_filter}
                }}
                ORDER BY {sample_order}
                LIMIT {sample_limit}
            }}
            {predicate_clause}
            ?s a erct:RandomisedControlledTrial ;
               ?p ?o .
        }}
        """

    try:
        timings.append(("before_sparql", time.perf_counter() - start_time))
        results = _execute_json_sparql(query)
    except Exception as exc:
        print(f"[kg] Failed to fetch knowledge graph data: {exc}")
        if stale_payload:
            fallback_payload = {**stale_payload, "stale": True, "error": str(exc)}
            response = make_response(jsonify(fallback_payload))
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['X-Cache'] = 'stale'
            return response
        return (
            jsonify(
                {
                    "error": "Failed to fetch knowledge graph data",
                    "details": str(exc),
                }
            ),
            500,
        )
    timings.append(("after_sparql", time.perf_counter() - start_time))

    bindings = results["results"]["bindings"]
    cleaned_data = _convert_bindings_to_trials(bindings)
    trial_map: Dict[str, Dict] = {trial["id"]: trial for trial in cleaned_data}

    ordered_trials: List[Dict] = []
    seen_ids = set()
    for trial in cleaned_data:
        ordered_trials.append(trial)
        seen_ids.add(trial["id"])

    if search_term and view_mode != "summary":
        timings.append(("before_semantic", time.perf_counter() - start_time))
        semantic_top_k = max(limit * 2, 25)
        if SEMANTIC_MAX_TOP_K:
            semantic_top_k = min(semantic_top_k, SEMANTIC_MAX_TOP_K)
        semantic_order: List[Tuple[str, float]] = semantic_searcher.search(
            search_term, top_k=semantic_top_k
        )
        if semantic_order:
            semantic_scores: Dict[str, float] = {}
            semantic_ids: List[str] = []
            for trial_id, score in semantic_order:
                if score < SEMANTIC_SCORE_THRESHOLD:
                    continue
                normalized_id = _normalize_trial_identifier(trial_id)
                if not normalized_id:
                    continue
                semantic_ids.append(normalized_id)
                semantic_scores[normalized_id] = score

            missing_ids = [tid for tid in semantic_ids if tid not in trial_map]
            additional_trials = _fetch_trials_by_ids(missing_ids)
            for trial in additional_trials:
                trial_map[trial["id"]] = trial

            for tid in semantic_ids:
                if tid in trial_map:
                    trial_map[tid]["semanticScore"] = semantic_scores.get(tid, 0.0)
                    if tid not in seen_ids:
                        ordered_trials.append(trial_map[tid])
                        seen_ids.add(tid)
        timings.append(("after_semantic", time.perf_counter() - start_time))

    timings.append(("before_sector_labels", time.perf_counter() - start_time))
    _enrich_trials_with_sector_labels(ordered_trials)
    timings.append(("after_sector_labels", time.perf_counter() - start_time))

    limited_data = ordered_trials[:limit]

    publication_refs = set()
    for trial in limited_data:
        for ref in _split_multi_value_field(trial.get("hasPublicationInfo")):
            publication_refs.add(ref)
    if publication_refs:
        timings.append(("before_pub_meta", time.perf_counter() - start_time))
        publication_metadata = _fetch_publication_metadata(list(publication_refs))
        timings.append(("after_pub_meta", time.perf_counter() - start_time))
    else:
        publication_metadata = {}
    if publication_metadata:
        for trial in limited_data:
            for ref in _split_multi_value_field(trial.get("hasPublicationInfo")):
                identifier = _normalize_trial_identifier(ref)
                meta = publication_metadata.get(identifier)
                if not meta:
                    continue
                doi = meta.get("doi")
                if doi and not trial.get("DOI"):
                    trial["DOI"] = doi
                paper_url = meta.get("url") or _normalise_doi_to_url(doi)
                if paper_url:
                    trial["paperUrl"] = paper_url
                if meta.get("title") and not trial.get("publicationTitle"):
                    trial["publicationTitle"] = meta["title"]
                break

    response_data = {
        "count": len(limited_data),
        "results": limited_data
    }
    
    #print(response_data["results"])

    if KNOWLEDGE_GRAPH_CACHE_TTL > 0:
        with _KG_CACHE_LOCK:
            _KG_CACHE[cache_key] = (time.time(), response_data)

    response = make_response(jsonify(response_data))
    response.headers['Access-Control-Allow-Origin'] = '*'
    if stale_payload:
        response.headers['X-Cache'] = 'refreshed'
    timings.append(("complete", time.perf_counter() - start_time))
    print(f"[kg/{request_id}] timings={timings}")
    
    return response


def _fetch_trials_by_ids(trial_ids: List[str]) -> List[Dict]:
    normalized_ids = []
    for trial_id in trial_ids:
        normalized = _normalize_trial_identifier(trial_id)
        if normalized:
            normalized_ids.append(normalized)

    if not normalized_ids:
        return []

    prefixes = """
    PREFIX erct: <https://erct.adaptcentre.com/ontology#>
    PREFIX gn: <http://www.geonames.org/ontology#>
    PREFIX ex: <https://interdev.adaptcentre.com/id/>
    """

    values_clause = " ".join([f"ex:{trial}" for trial in normalized_ids])
    predicate_clause = _build_predicate_values_clause(FULL_TRIAL_PREDICATES)
    query = f"""
    {prefixes}
    SELECT ?s ?p ?o
    WHERE {{
        VALUES ?s {{ {values_clause} }}
        {predicate_clause}
        ?s a erct:RandomisedControlledTrial ;
           ?p ?o .
    }}
    """

    try:
        results = _execute_json_sparql(query)
    except Exception as exc:
        print(f"[semantic-search] Failed to fetch trials by ids {normalized_ids}: {exc}")
        return []

    bindings = results.get("results", {}).get("bindings", [])
    trials = _convert_bindings_to_trials(bindings)
    _enrich_trials_with_sector_labels(trials)
    return trials


def _fetch_publication_metadata(publication_refs: List[str]) -> Dict[str, Dict[str, str]]:
    identifier_to_curie: Dict[str, str] = {}
    for ref in publication_refs:
        if not ref:
            continue
        normalized_id = _normalize_trial_identifier(ref)
        curie = _convert_to_trial_curie(ref)
        if not normalized_id or not curie:
            continue
        identifier_to_curie[normalized_id] = curie

    if not identifier_to_curie:
        return {}

    values_clause = " ".join(sorted(set(identifier_to_curie.values())))
    prefixes = """
    PREFIX erct: <https://erct.adaptcentre.com/ontology#>
    PREFIX ex: <https://interdev.adaptcentre.com/id/>
    """
    query = f"""
    {prefixes}
    SELECT ?pub ?doi ?title ?url
    WHERE {{
        VALUES ?pub {{ {values_clause} }}
        OPTIONAL {{ ?pub erct:hasDOI ?doi }}
        OPTIONAL {{ ?pub erct:hasTitle ?title }}
        OPTIONAL {{ ?pub erct:hasURL ?url }}
    }}
    """
    try:
        results = _execute_json_sparql(query)
    except Exception as exc:
        print(f"[kg] Failed to fetch publication metadata: {exc}")
        return {}

    metadata: Dict[str, Dict[str, str]] = {}
    for binding in results.get("results", {}).get("bindings", []):
        pub_uri = binding.get("pub", {}).get("value")
        if not pub_uri:
            continue
        identifier = _normalize_trial_identifier(pub_uri)
        if not identifier:
            continue
        record = metadata.setdefault(identifier, {})
        doi = binding.get("doi", {}).get("value")
        if doi:
            record["doi"] = doi.strip()
        title = binding.get("title", {}).get("value")
        if title:
            record["title"] = title.strip()
        url = binding.get("url", {}).get("value")
        if url:
            record["url"] = url.strip()
    return metadata

@main.route('/add_knowledge_graph_entry', methods=['POST'])
def add_knowledge_graph_entry():
    data = request.get_json(force=True, silent=True) or {}
    participant = request.headers.get("X-Participant-Name", "").strip() or "anonymous"

    abstract = _escape_sparql_literal(data.get('Abstract', ''))
    authors = _escape_sparql_literal(data.get('Authors', ''))
    title = _escape_sparql_literal(data.get('Title', ''))
    sector = _escape_sparql_literal(data.get('Sector', ''))
    country_code = _escape_sparql_literal(data.get('countryCode', ''))
    keywords = _escape_sparql_literal(data.get('Keywords', ''))
    evaluation_design = _escape_sparql_literal(data.get('Evaluation_design', ''))
    unsustainable_goals = _escape_sparql_literal(data.get('UNSustainableGoals', ''))

    selected_ai = str(data.get("SelectedAI", "")).strip() or "Manual"
    selected_ai_escaped = _escape_sparql_literal(selected_ai)
    uploaded_source_name = (
        str(data.get("SourceDocumentTitle", "")).strip()
        or str(data.get("Title", "")).strip()
        or "Submitted source document"
    )
    uploaded_source_name_escaped = _escape_sparql_literal(uploaded_source_name)
    participant_label = _escape_sparql_literal(participant)

    model_name_map = {
        "GPT": "gpt-4o",
        "Google_Gemini": "gemini-1.5-pro",
        "Claude_Anthropic": "claude-3-5-sonnet-20241022",
        "Manual": "manual-entry",
    }
    model_name = model_name_map.get(selected_ai, selected_ai or "manual-entry")
    model_name_escaped = _escape_sparql_literal(model_name)

    uuid_val = uuid.uuid4()
    trial_curie = f"ex:{uuid_val}"
    submission_curie = f"ex:submission-{uuid_val}"
    extraction_curie = f"ex:extraction-{uuid_val}"
    source_document_curie = f"ex:source-document-{uuid_val}"
    reviewer_curie = f"ex:participant-{_slugify_identifier(participant, fallback='anonymous')}"
    ingestion_method_curie = f"ex:ingestion-method-{_slugify_identifier(selected_ai, fallback='manual')}"

    timestamp_iso = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    prefixes = """
    PREFIX erct: <https://erct.adaptcentre.com/ontology#>
    PREFIX ex: <https://interdev.adaptcentre.com/id/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    PREFIX gn: <http://www.geonames.org/ontology#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    """

    query = f"""
    {prefixes}
    INSERT DATA {{
        {trial_curie} a erct:RandomisedControlledTrial ;
                      erct:Abstract "{abstract}" ;
                      erct:hasAbstract "{abstract}" ;
                      erct:Authors "{authors}" ;
                      erct:Title "{title}" ;
                      erct:hasName "{title}" ;
                      erct:Sector "{sector}" ;
                      erct:hasUNSustainableGoal "{unsustainable_goals}" ;
                      gn:countryCode "{country_code}" ;
                      erct:Keywords "{keywords}" ;
                      erct:Evaluation_design "{evaluation_design}" ;
                      erct:hasSubmission {submission_curie} .

        {submission_curie} a erct:Submission ;
                           erct:hasExtractionRun {extraction_curie} ;
                           erct:ingestionMethod {ingestion_method_curie} ;
                           erct:reviewedBy {reviewer_curie} ;
                           erct:reviewTimestamp "{timestamp_iso}"^^xsd:dateTime .

        {extraction_curie} a erct:ExtractionRun ;
                           erct:extractedFromDocument {source_document_curie} ;
                           erct:extractionTimestamp "{timestamp_iso}"^^xsd:dateTime ;
                           erct:usedModelName "{model_name_escaped}" ;
                           erct:usedModelVersion "{selected_ai_escaped}" .

        {source_document_curie} a erct:SourceDocument ;
                                erct:hasTitle "{uploaded_source_name_escaped}" .

        {reviewer_curie} a erct:Researcher ;
                         erct:hasName "{participant_label}" .

        {ingestion_method_curie} a erct:IngestionMethod ;
                                 rdfs:label "{selected_ai_escaped}" .
    }}
    """

    try:
        _execute_sparql_update(query)
        return jsonify({'message': 'Entry added successfully', 'uuid': str(uuid_val)})
    except Exception as err:
        return jsonify({'error': 'Failed to execute query', 'details': str(err)}), 500



@main.route('/categories', methods=['GET'])
def fetch_categories():
    # Accept category as provided, normalize to known keys
    raw_category = request.args.get('category', default='Sector', type=str) or 'Sector'
    norm = raw_category.strip()
    # Map common variants to expected predicate
    category_map = {
        'sector': '(erct:Sector|erct:hasSector/(erct:hasName|skos:prefLabel))',
        'title': '(erct:hasName|erct:Title)',
        'authors': 'erct:Authors',
        'keywords': 'erct:Keywords',
        'language': 'erct:Language',
        'country': 'gn:countryCode',
        'countrycode': 'gn:countryCode',
        'subsector': 'erct:Sub-sector',
        'sub-sector': 'erct:Sub-sector',
        'sub_sector': 'erct:Sub-sector',
        'evaluationdesign': 'erct:Evaluation_design',
        'evaluation_design': 'erct:Evaluation_design',
        'equityfocus': 'erct:Equity_focus',
        'equity_focus': 'erct:Equity_focus',
        'programfundingagency': '(erct:Program_funding_agency|erct:Research_funding_agency)',
        'program_funding_agency': '(erct:Program_funding_agency|erct:Research_funding_agency)',
        'implementationagency': 'erct:Implementation_agency',
        'implementation_agency': 'erct:Implementation_agency',
        'unitofobservation': 'erct:Unit_of_observation',
        'unit_of_observation': 'erct:Unit_of_observation',
    }
    predicate = category_map.get(norm.replace(" ", "").lower())
    if predicate is None:
        # Fallback to erct:<Category> with the original value (no title-casing)
        predicate = f"erct:{norm}"

    try:
        sparql = SPARQLWrapper(GRAPHDB_SPARQL_ENDPOINT)

        prefixes = """
        PREFIX ex: <https://interdev.adaptcentre.com/id/>
        PREFIX erct: <https://erct.adaptcentre.com/ontology#>
        PREFIX gn: <http://www.geonames.org/ontology#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        """

        query = f"""
        {prefixes}
        SELECT DISTINCT ?value
        WHERE {{
            ?trial a erct:RandomisedControlledTrial ;
                   {predicate} ?value .
        }}
        """

        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()

        # Build response list
        bindings = results.get("results", {}).get("bindings", [])
        categories = []
        for b in bindings:
            raw_value = b.get("value", {}).get("value")
            if not raw_value:
                continue
            entry = {"name": raw_value, "value": raw_value}
            categories.append(entry)

        # Optional pretty names for Country
        if predicate == 'gn:countryCode':
            pretty = []
            for b in bindings:
                code = (b.get("value", {}).get("value") or "").strip()
                if not code:
                    continue
                country = pycountry.countries.get(alpha_2=code.upper()) if len(code) == 2 else None
                display_name = country.name if country else code
                pretty.append({"name": display_name, "value": code.upper()})
            categories = pretty

        response_data = {"count": len(categories), "results": categories}
        return jsonify(response_data)
    except Exception as e:
        # Log and return a 500 with a clear message
        print(f"/categories error for category='{raw_category}': {e}")
        return jsonify({"error": "Failed to fetch categories", "details": str(e)}), 500

# Do not override CORS from flask_cors; it is already configured above
# Keeping this hook minimal avoids conflicts with nginx and multiple origins
@app.after_request
def add_cors_headers(response):
    response.headers.setdefault("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
    response.headers.setdefault(
        "Access-Control-Allow-Headers",
        "Content-Type, Authorization, X-Participant-Name",
    )
    return response


app.register_blueprint(main)
if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True, port=5000)
