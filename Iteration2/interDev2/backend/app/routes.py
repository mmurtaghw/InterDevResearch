# Routes.py

from flask import Flask, Blueprint, jsonify, request, make_response
from werkzeug.utils import secure_filename
import os
from SPARQLWrapper import JSON, SPARQLWrapper
import uuid
import requests
from flask_cors import CORS
from flask import send_from_directory
import pycountry
from openai import OpenAI
from dotenv import load_dotenv 
from pdfminer.high_level import extract_text
from urllib.parse import unquote
from rdflib import Graph, RDF, URIRef
import google.generativeai as genai
import anthropic
from datetime import datetime
import time 
import re
import json
import traceback

UPLOAD_FOLDER = '/home/mwhite/interDev/backend/uploads'

ALLOWED_EXTENSIONS = {'pdf'}

load_dotenv()

# STATIC_FOLDER = os.path.abspath("/home/mwhite/interDev/interface/interface")

# print(STATIC_FOLDER)

app = Flask(__name__, static_url_path=None)


app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER 

CORS(app, resources={
    r"/*": {"origins": "http://vma45.scss.tcd.ie"},
    r"/api/*": {"origins": "http://vma45.scss.tcd.ie"},
    r"/*": {"origins": "https://interdev2.adaptcentre.ie"},
    r"/api/*": {"origins": "https://interdev2.adaptcentre.ie"}
})


main = Blueprint('main', __name__)


# CORS(main)  # Not needed as CORS is already enabled globally

client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
anthropicClient = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

KEY_ALIASES = {
    "hasName": "Title",
    "hasTitle": "Title",
    "hasAbstract": "Abstract",
    "hasSector": "Sector",
    "Sub-sector": "Sub_sector",
    "Pre-Registration": "Pre_Registration",
    "Protocol_Pre-Analysis_Plan": "Protocol_Pre_Analysis_Plan",
    "State%2FProvince_name": "State_Province_name",
    "State/Province_name": "State_Province_name",
}

GRAPHDB_BASE_URL = os.getenv("GRAPHDB_BASE_URL", "http://vma49.scss.tcd.ie:7200").rstrip("/")
GRAPHDB_REPOSITORY = os.getenv("GRAPHDB_REPOSITORY", "RCT")
GRAPHDB_REPOSITORY_URL = f"{GRAPHDB_BASE_URL}/repositories/{GRAPHDB_REPOSITORY}"
GRAPHDB_STATEMENTS_URL = f"{GRAPHDB_REPOSITORY_URL}/statements"
ERCT_NS = "https://erct.adaptcentre.com/ontology#"
GN_NS = "http://www.geonames.org/ontology#"
SKOS_NS = "http://www.w3.org/2004/02/skos/core#"
RDFS_NS = "http://www.w3.org/2000/01/rdf-schema#"
COLLECTION_BASE_URI = "https://interdev.adaptcentre.com/collection/"


def _normalize_text(value):
    return str(value).replace("\u00a0", " ").strip()


def _extract_local_name(uri):
    text = str(uri)
    if "#" in text:
        return text.split("#")[-1]
    if "/" in text:
        return text.rstrip("/").split("/")[-1]
    return text


def _subject_id(subject):
    subject_str = str(subject)
    local = _extract_local_name(subject_str)
    return local.split(":")[-1]


def _sparql_escape(value):
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def _is_uri(value):
    return isinstance(value, str) and value.startswith(("http://", "https://", "urn:"))


def _safe_predicate_local_name(value):
    return re.sub(r"[^A-Za-z0-9_]", "_", str(value)).strip("_") or "field"


def _collection_uri_from_name(name):
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower()).strip("-")
    if not slug:
        slug = "unnamed-collection"
    return f"{COLLECTION_BASE_URI}{slug}"


def _candidate_subject_uris(trial_id):
    raw = (trial_id or "").strip()
    if not raw:
        return []
    uris = []
    if _is_uri(raw):
        uris.append(raw)
    tail = raw.split(":")[-1]
    uris.extend([
        f"https://interdev.adaptcentre.com/id/{tail}",
        f"urn:uuid:{tail}",
    ])
    return list(dict.fromkeys(uris))


def _resolve_trial_uri(trial_id):
    candidates = _candidate_subject_uris(trial_id)
    if not candidates:
        return None

    values_clause = " ".join(f"<{uri}>" for uri in candidates)
    query = f"""
    PREFIX erct: <{ERCT_NS}>
    SELECT ?s
    WHERE {{
        VALUES ?s {{ {values_clause} }}
        ?s a erct:RandomisedControlledTrial .
    }}
    LIMIT 1
    """
    try:
        results = _run_sparql_query(query, return_format=JSON)
        bindings = results.get("results", {}).get("bindings", [])
        if bindings:
            return bindings[0]["s"]["value"]
    except Exception:
        pass

    return candidates[0]


def _execute_sparql_update(query):
    headers = {
        "Content-Type": "application/sparql-update",
        "Accept": "application/sparql-results+json",
    }
    response = requests.post(
        GRAPHDB_STATEMENTS_URL,
        data=query.encode("utf-8"),
        headers=headers,
    )
    response.raise_for_status()
    return response


def _build_subject_values_clause(trial_ids):
    subject_uris = []
    for trial_id in trial_ids or []:
        raw = (trial_id or "").strip()
        if not raw:
            continue
        if raw.startswith(("http://", "https://", "urn:")):
            subject_uris.append(f"<{raw}>")
        tail = raw.split(":")[-1]
        subject_uris.append(f"<https://interdev.adaptcentre.com/id/{tail}>")
        subject_uris.append(f"<urn:uuid:{tail}>")

    deduped = list(dict.fromkeys(subject_uris))
    if not deduped:
        return ""
    return "VALUES ?s { " + " ".join(deduped) + " }"


def _filter_predicate_expression(filter_key):
    mapping = {
        "Abstract": f"<{ERCT_NS}Abstract>|<{ERCT_NS}hasAbstract>",
        "Authors": f"<{ERCT_NS}Authors>",
        "Sector": f"<{ERCT_NS}Sub-sector>|<{ERCT_NS}hasSector>",
        "Title": f"<{ERCT_NS}hasName>|<{ERCT_NS}Title>|<{ERCT_NS}hasTitle>",
        "Keywords": f"<{ERCT_NS}Keywords>",
        "Language": f"<{ERCT_NS}Language>",
        "countryCode": f"<{GN_NS}countryCode>|<{ERCT_NS}hasCountry>",
        "Country": f"<{GN_NS}countryCode>|<{ERCT_NS}hasCountry>",
        # Prefer canonical methodology links; hasMethodology points to per-trial method nodes and is too granular for filtering.
        "Methodology": f"<{ERCT_NS}hasEvaluationMethod>|<http://www.semanticweb.org/ERCT#hasMethod>",
        "InterventionType": f"<{ERCT_NS}hasInterventionType>",
        "OutcomeDomain": f"<{ERCT_NS}hasOutcomeDomain>",
    }
    return mapping.get(filter_key)


def _build_filter_patterns(filters):
    patterns = []
    pattern_index = 0
    for filter_key, values in (filters or {}).items():
        predicate_expr = _filter_predicate_expression(filter_key)
        if not predicate_expr:
            continue
        for value in values:
            if value is None:
                continue
            pattern_index += 1
            escaped_value = _sparql_escape(value)
            filter_var = f"f{pattern_index}"
            if _is_uri(value):
                patterns.append(f"?s ({predicate_expr}) <{escaped_value}> .")
            else:
                patterns.append(
                    f"""
                    ?s ({predicate_expr}) ?{filter_var} .
                    FILTER(
                        LCASE(STR(?{filter_var})) = LCASE("{escaped_value}")
                        || EXISTS {{
                            ?{filter_var} <{RDFS_NS}label> ?{filter_var}_label .
                            FILTER(LCASE(STR(?{filter_var}_label)) = LCASE("{escaped_value}"))
                        }}
                        || EXISTS {{
                            ?{filter_var} <{SKOS_NS}prefLabel> ?{filter_var}_pref .
                            FILTER(LCASE(STR(?{filter_var}_pref)) = LCASE("{escaped_value}"))
                        }}
                    )
                    """
                )
    return "\n".join(patterns)


def _run_sparql_query(query, return_format=JSON):
    sparql = SPARQLWrapper(GRAPHDB_REPOSITORY_URL)
    sparql.setTimeout(int(os.getenv("SPARQL_TIMEOUT_SECONDS", "20")))
    sparql.setQuery(query)
    sparql.setReturnFormat(return_format)
    return sparql.query().convert()


def _results_to_clean_trials(results):
    processed_data = {}
    for result in results.get("results", {}).get("bindings", []):
        subject = result["s"]["value"]
        trial_id = _subject_id(subject)

        if subject not in processed_data:
            processed_data[subject] = {"id": trial_id}

        predicate = result["p"]["value"]
        object_value = result["o"]["value"]

        if predicate in processed_data[subject]:
            if not isinstance(processed_data[subject][predicate], list):
                processed_data[subject][predicate] = [processed_data[subject][predicate]]
            processed_data[subject][predicate].append(object_value)
        else:
            processed_data[subject][predicate] = object_value

    cleaned_data = [clean_trial(trial) for trial in processed_data.values()]
    return [
        trial for trial in cleaned_data
        if trial.get("Abstract") and trial.get("Authors") and trial.get("Title")
    ]

def log_submission(model_name, content_submitted):
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
    
    # Replace colons in timestamp for filename compatibility
    safe_timestamp = timestamp.replace(":", "-")
    filename = os.path.join(logs_folder, f"{model_name}_{safe_timestamp}.json")
    
    with open(filename, "w") as f:
        json.dump(log_data, f, indent=2)

    
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
            'http://example.org/ercgt#Abstract': 'Abstract',
            'http://example.org/ercgt#Authors': 'Authors',
            'http://example.org/ercgt#Title': 'Title',
            'http://example.org/ercgt#Sector': 'Sector',
            'http://example.org/ercgt#Primary_Dataset_Availability': 'Primary_Dataset_Availability',
            'http://example.org/ercgt#Open_Access': 'Open_Access',
            'http://example.org/ercgt#Sub-sector': 'Sub_sector',
            'http://example.org/ercgt#Program_funding_agency': 'Program_funding_agency',
            'http://example.org/ercgt#Evaluation_design': 'Evaluation_design',
            'http://example.org/ercgt#Language': 'Language',
            'http://example.org/ercgt#Equity_focus': 'Equity_focus',
            'http://example.org/ercgt#CRS_Voluntary_DAC_Code': 'CRS_Voluntary_DAC_Code',
            'http://example.org/ercgt#Project_name': 'Project_name',
            'http://example.org/ercgt#Protocol_Pre-Analysis_Plan': 'Protocol_Pre-Analysis_Plan',
            'http://example.org/ercgt#Unit_of_observation': 'Unit_of_observation',
            'http://example.org/ercgt#Keywords': 'Keywords',
            'http://example.org/ercgt#Ethics_Approval': 'Ethics_Approval',
            'http://example.org/ercgt#Pre-Registration': 'Pre_Registration',
            'http://example.org/ercgt#DOI': 'DOI',
            'http://example.org/ercgt#Received_date': 'Received_date',
            'http://example.org/ercgt#Revised_date': 'Revised_date',
            'http://example.org/ercgt#Accepted_date': 'Accepted_date',
            'http://www.geonames.org/ontology#countryCode': 'countryCode',
            'http://www.geonames.org/ontology#lat': 'latitude',
            'http://www.geonames.org/ontology#long': 'longitude',
            'http://www.geonames.org/ontology#name': 'countryName',
            'http://www.geonames.org/ontology#population': 'population',
            'http://www.semanticweb.org/ERCT#hasOutcome': 'Outcomes',
            'http://www.semanticweb.org/ERCT#hasMethod': 'Methodology',
        }

        trial_data = {}

        # Extract main trial subject
        trial_subjects = [
            s for s in graph.subjects(RDF.type, URIRef("http://www.semanticweb.org/ERCT#RandomisedControlledTrial"))
        ]
        if not trial_subjects:
            return jsonify({'error': 'No subjects of type RandomisedControlledTrial found'}), 404
        main_subject = trial_subjects[0]

        # General trial data extraction
        for predicate, obj in graph.predicate_objects(main_subject):
            pred_str = str(predicate)
            key = key_map.get(pred_str, pred_str.split("/")[-1])
            value = str(obj)

            if key in trial_data:
                if not isinstance(trial_data[key], list):
                    trial_data[key] = [trial_data[key]]
                trial_data[key].append(value)
            else:
                trial_data[key] = value

        # Extract Outcome details
        outcome_texts = []
        for outcome in graph.subjects(RDF.type, URIRef("http://www.semanticweb.org/ERCT#Outcome")):
            for predicate, obj in graph.predicate_objects(outcome):
                pred_str = str(predicate)
                if pred_str.endswith('hasType'):
                    outcome_texts.append(str(obj))
        if outcome_texts:
            trial_data['Outcomes'] = '; '.join(outcome_texts)

        # Extract Methodology details
        methodology_texts = []
        for method in graph.subjects(RDF.type, URIRef("http://www.semanticweb.org/ERCT#Method")):
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

def process_with_gpt(extracted_text):
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

    log_submission("gpt4o", response.choices[0].message.content)

    return response.choices[0].message.content

def process_with_google_gemini(extracted_text, max_retries=5):
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
            log_submission("gemini-1.5", response.result)

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



def process_with_claude(extracted_text, max_retries=5):
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
            log_submission("claude", response['completion'])

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
                response = process_with_gpt(extracted_text)
            elif selected_ai == 'Google_Gemini':
                response = process_with_google_gemini(extracted_text)
            elif selected_ai == 'Claude_Anthropic':
                response = process_with_claude(extracted_text)
            else:
                return jsonify({'error': f'Unsupported AI model: {selected_ai}'}), 400

            # Return the response
            return jsonify({"response": response})

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
        # Remove non-standard characters and namespaces from keys
        clean_key = unquote(_extract_local_name(key)).replace("/", "_")
        clean_key = KEY_ALIASES.get(clean_key, clean_key)
        
        # Flatten arrays into a single string if necessary
        if isinstance(value, list):
            normalized_values = [_normalize_text(v) for v in value if _normalize_text(v)]
            deduplicated_values = list(dict.fromkeys(normalized_values))
            value = ", ".join(deduplicated_values)
        
        # Formatting text
        if isinstance(value, str):
            value = _normalize_text(value)  # Replace non-breaking spaces

        if clean_key in cleaned_trial and cleaned_trial[clean_key] != value:
            cleaned_trial[clean_key] = f"{cleaned_trial[clean_key]}, {value}"
        else:
            cleaned_trial[clean_key] = value

    if cleaned_trial.get("Sub_sector"):
        cleaned_trial["Sector"] = cleaned_trial["Sub_sector"]
    
    return cleaned_trial


@main.route('/collections', methods=['GET'])
def fetch_collections():
    query = f"""
    PREFIX skos: <{SKOS_NS}>
    SELECT ?collection ?name ?trial
    WHERE {{
        ?collection a skos:Collection .
        OPTIONAL {{ ?collection skos:prefLabel ?name . }}
        OPTIONAL {{ ?collection skos:member ?trial . }}
    }}
    ORDER BY ?name ?collection ?trial
    """
    results = _run_sparql_query(query, return_format=JSON)
    grouped = {}
    for binding in results.get("results", {}).get("bindings", []):
        collection_uri = binding["collection"]["value"]
        name = _normalize_text(binding.get("name", {}).get("value") or _extract_local_name(collection_uri))
        trial_uri = binding.get("trial", {}).get("value")

        if collection_uri not in grouped:
            grouped[collection_uri] = {
                "id": collection_uri,
                "name": name,
                "trialIds": [],
            }

        if trial_uri:
            grouped[collection_uri]["trialIds"].append(_subject_id(trial_uri))

    collections = []
    for collection in grouped.values():
        collection["trialIds"] = list(dict.fromkeys(collection["trialIds"]))
        collections.append(collection)
    response = make_response(jsonify({
        "count": len(collections),
        "results": collections,
    }))
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response


@main.route('/collections', methods=['POST'])
def create_collection():
    data = request.get_json() or {}
    name = _normalize_text(data.get("name", ""))
    if not name:
        return jsonify({"error": "Collection name is required"}), 400

    collection_uri = _collection_uri_from_name(name)
    escaped_name = _sparql_escape(name)
    query = f"""
    PREFIX skos: <{SKOS_NS}>
    INSERT {{
        <{collection_uri}> a skos:Collection ;
            skos:prefLabel "{escaped_name}" .
    }}
    WHERE {{
        FILTER NOT EXISTS {{ <{collection_uri}> a skos:Collection . }}
    }}
    """
    try:
        _execute_sparql_update(query)
        return jsonify({"message": "Collection created", "id": collection_uri, "name": name}), 201
    except requests.HTTPError as err:
        return jsonify({"error": "Failed to create collection", "details": str(err)}), 500


@main.route('/collections/trials', methods=['POST'])
def add_trial_to_collection():
    data = request.get_json() or {}
    collection_name = _normalize_text(data.get("collectionName", ""))
    trial_id = _normalize_text(data.get("trialId", ""))
    if not collection_name or not trial_id:
        return jsonify({"error": "collectionName and trialId are required"}), 400

    collection_uri = _collection_uri_from_name(collection_name)
    trial_uri = _resolve_trial_uri(trial_id)
    if not trial_uri:
        return jsonify({"error": "Could not resolve trial URI"}), 400

    escaped_name = _sparql_escape(collection_name)
    query = f"""
    PREFIX skos: <{SKOS_NS}>
    INSERT {{
        <{collection_uri}> a skos:Collection ;
            skos:prefLabel "{escaped_name}" ;
            skos:member <{trial_uri}> .
    }}
    WHERE {{
        OPTIONAL {{ <{collection_uri}> a skos:Collection . }}
        FILTER NOT EXISTS {{ <{collection_uri}> skos:member <{trial_uri}> . }}
    }}
    """
    try:
        _execute_sparql_update(query)
        return jsonify({"message": "Trial added to collection"}), 200
    except requests.HTTPError as err:
        return jsonify({"error": "Failed to add trial to collection", "details": str(err)}), 500


@main.route('/collections/trials', methods=['DELETE'])
def remove_trial_from_collection():
    data = request.get_json() or {}
    collection_name = _normalize_text(data.get("collectionName", ""))
    trial_id = _normalize_text(data.get("trialId", ""))
    if not collection_name or not trial_id:
        return jsonify({"error": "collectionName and trialId are required"}), 400

    collection_uri = _collection_uri_from_name(collection_name)
    trial_uri = _resolve_trial_uri(trial_id)
    if not trial_uri:
        return jsonify({"error": "Could not resolve trial URI"}), 400

    query = f"""
    PREFIX skos: <{SKOS_NS}>
    DELETE DATA {{
        <{collection_uri}> skos:member <{trial_uri}> .
    }}
    """
    try:
        _execute_sparql_update(query)
        return jsonify({"message": "Trial removed from collection"}), 200
    except requests.HTTPError as err:
        return jsonify({"error": "Failed to remove trial from collection", "details": str(err)}), 500

@main.route('/download_knowledge_graph_data', methods=['GET'])
def download_knowledge_graph_data():
    trial_ids = request.args.getlist('trialIds')
    filters = request.args.to_dict(flat=False)
    filters.pop('trialIds', None)
    filters.pop('format', None)
    download_format = request.args.get('format', 'turtle').lower()

    values_clause = _build_subject_values_clause(trial_ids)
    filter_patterns = _build_filter_patterns(filters)
    prefixes = """
    PREFIX erct: <https://erct.adaptcentre.com/ontology#>
    PREFIX gn: <http://www.geonames.org/ontology#>
    PREFIX ex: <https://interdev.adaptcentre.com/id/>
    """

    if download_format == "csv":
        query = f"""
        {prefixes}
        SELECT ?s ?p ?o
        WHERE {{
            {values_clause}
            ?s a erct:RandomisedControlledTrial ;
               ?p ?o .
            {filter_patterns}
        }}
        ORDER BY ?s ?p ?o
        """
        results = _run_sparql_query(query, return_format='csv')
        response = make_response(results)
        response.headers['Content-Type'] = 'text/csv'
    elif download_format == "json":
        query = f"""
        {prefixes}
        SELECT ?s ?p ?o
        WHERE {{
            {values_clause}
            ?s a erct:RandomisedControlledTrial ;
               ?p ?o .
            {filter_patterns}
        }}
        ORDER BY ?s ?p ?o
        """
        results = _run_sparql_query(query, return_format=JSON)
        filtered_data = _results_to_clean_trials(results)
        response = make_response(jsonify({
            "count": len(filtered_data),
            "results": filtered_data,
        }))
        response.headers['Content-Type'] = 'application/json'
    else:
        query = f"""
        {prefixes}
        CONSTRUCT {{ ?s ?p ?o }}
        WHERE {{
            {values_clause}
            ?s a erct:RandomisedControlledTrial ;
               ?p ?o .
            {filter_patterns}
        }}
        """
        results = _run_sparql_query(query, return_format='turtle')
        response = make_response(results)
        response.headers['Content-Type'] = 'text/turtle'

    return response



@main.route('/knowledge_graph_data', methods=['GET'])
def fetch_knowledge_graph_data():    
    trial_ids = request.args.getlist('trialIds')  # Get multiple trialIds
    limit = request.args.get('limit', default=5, type=int)  # Fetch the limit
    filters = request.args.to_dict(flat=False)
    filters.pop('limit', None)  # Remove 'limit' if present in filters
    filters.pop('trialIds', None)  # Remove 'trialIds' if present in filters

    values_clause = _build_subject_values_clause(trial_ids)
    filter_patterns = _build_filter_patterns(filters)
    prefixes = """
    PREFIX erct: <https://erct.adaptcentre.com/ontology#>
    PREFIX gn: <http://www.geonames.org/ontology#>
    PREFIX ex: <https://interdev.adaptcentre.com/id/>
    """

    query = f"""
    {prefixes}
    SELECT ?s ?p ?o
    WHERE {{
        {values_clause}
        ?s a erct:RandomisedControlledTrial ;
           ?p ?o .
        {filter_patterns}
    }}
    ORDER BY ?s ?p ?o
    """

    results = _run_sparql_query(query, return_format=JSON)
    filtered_data = _results_to_clean_trials(results)
    limited_data = filtered_data[:limit]

    response_data = {
        "count": len(limited_data),
        "results": limited_data
    }

    #print(response_data["results"])

    response = make_response(jsonify(response_data))
    response.headers['Access-Control-Allow-Origin'] = '*'
    
    return response

@main.route('/add_knowledge_graph_entry', methods=['POST'])
def add_knowledge_graph_entry():
    data = request.get_json() or {}
    if not isinstance(data, dict):
        return jsonify({'error': 'Invalid JSON payload'}), 400

    # Generate a unique identifier for the new trial
    uuid_val = uuid.uuid4()
    trial_uri = f"https://interdev.adaptcentre.com/id/{uuid_val}"

    field_predicate_map = {
        "Abstract": f"{ERCT_NS}hasAbstract",
        "Authors": f"{ERCT_NS}Authors",
        "Title": f"{ERCT_NS}hasTitle",
        "Sector": f"{ERCT_NS}Sub-sector",
        "Sub_sector": f"{ERCT_NS}Sub-sector",
        "Keywords": f"{ERCT_NS}Keywords",
        "Evaluation_design": f"{ERCT_NS}Evaluation_design",
        "UNSustainableGoals": f"{ERCT_NS}UNSustainableGoals",
        "Methodology": f"{ERCT_NS}Methodology",
        "Outcomes": f"{ERCT_NS}Outcomes",
        "countryCode": f"{GN_NS}countryCode",
        "countryName": f"{GN_NS}name",
        "population": f"{GN_NS}population",
        "latitude": f"{GN_NS}lat",
        "longitude": f"{GN_NS}long",
    }

    triples = [f"<{trial_uri}> a <{ERCT_NS}RandomisedControlledTrial> ."]
    for key, raw_value in data.items():
        if raw_value is None:
            continue
        value = _normalize_text(raw_value)
        if not value:
            continue

        if key == "SelectedAI":
            predicate_uri = f"{ERCT_NS}ingestionMethod"
        else:
            predicate_uri = field_predicate_map.get(
                key,
                f"{ERCT_NS}{_safe_predicate_local_name(key)}",
            )

        escaped_value = _sparql_escape(value)
        triples.append(f"<{trial_uri}> <{predicate_uri}> \"{escaped_value}\" .")

    # Re-serialize and validate before insertion.
    turtle_data = "\n".join(triples)
    try:
        graph = Graph()
        graph.parse(data=turtle_data, format="turtle")
    except Exception as err:
        return jsonify({
            "error": "Validation failed: generated RDF is invalid.",
            "details": str(err),
        }), 400

    query = f"""
    INSERT DATA {{
        {turtle_data}
    }}
    """

    try:
        _execute_sparql_update(query)
        return jsonify({'message': 'Entry added successfully', 'uuid': str(uuid_val)})
    except requests.HTTPError as err:
        return jsonify({'error': 'Failed to execute query', 'details': str(err)}), 500



@main.route('/categories', methods=['GET'])
def fetch_categories():
    requested_category = request.args.get('category', default='Sector', type=str)
    normalized_category = (requested_category or 'Sector').strip()
    lookup_key = normalized_category.lower()

    if lookup_key in {'country', 'countrycode'}:
        predicate_expr = f"<{GN_NS}countryCode>|<{ERCT_NS}hasCountry>"
    elif lookup_key == 'sector':
        predicate_expr = f"<{ERCT_NS}Sub-sector>|<{ERCT_NS}hasSector>"
    elif lookup_key == 'methodology':
        predicate_expr = f"<{ERCT_NS}hasEvaluationMethod>|<http://www.semanticweb.org/ERCT#hasMethod>"
    elif lookup_key == 'interventiontype':
        predicate_expr = f"<{ERCT_NS}hasInterventionType>"
    elif lookup_key == 'outcomedomain':
        predicate_expr = f"<{ERCT_NS}hasOutcomeDomain>"
    else:
        mapped_expr = _filter_predicate_expression(normalized_category)
        if mapped_expr:
            predicate_expr = mapped_expr
        else:
            predicate_expr = f"<{ERCT_NS}{_sparql_escape(normalized_category)}>"

    query = f"""
    PREFIX erct: <{ERCT_NS}>
    PREFIX rdfs: <{RDFS_NS}>
    PREFIX skos: <{SKOS_NS}>
    SELECT DISTINCT ?value ?label
    WHERE {{
        ?trial a erct:RandomisedControlledTrial ;
               ({predicate_expr}) ?value .
        OPTIONAL {{ ?value rdfs:label ?rdfsLabel . }}
        OPTIONAL {{ ?value skos:prefLabel ?prefLabel . }}
        OPTIONAL {{ ?value erct:hasName ?erctName . }}
        BIND(COALESCE(?rdfsLabel, ?prefLabel, ?erctName, ?value) AS ?label)
    }}
    ORDER BY ?label
    """
    results = _run_sparql_query(query, return_format=JSON)

    dedup = {}
    for binding in results.get("results", {}).get("bindings", []):
        value = _normalize_text(binding.get("value", {}).get("value", ""))
        label = _normalize_text(binding.get("label", {}).get("value", value))
        if not value:
            continue

        if lookup_key in {"country", "countrycode"} and len(value) == 2 and value.isalpha():
            country = pycountry.countries.get(alpha_2=value.upper())
            display_name = country.name if country else label
            # Prefer ISO-2 code-backed entries over equivalent URI-backed labels.
            dedup[(display_name,)] = {"name": display_name, "value": value}
        elif lookup_key in {"country", "countrycode"}:
            dedup.setdefault((label,), {"name": label, "value": value})
        else:
            dedup[(label, value)] = {"name": label, "value": value}

    categories = list(dedup.values())

    # Wrap the results in a response object
    response_data = {
        "count": len(categories),
        "results": categories
    }


    response = make_response(jsonify(response_data))
    response.headers['Access-Control-Allow-Origin'] = '*'
    
    return response

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "http://vma45.scss.tcd.ie"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


app.register_blueprint(main)
if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True, port=5000)
