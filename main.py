# main_enhanced.py
# Enhanced Offline Waste Sorter — Streamlit app (Image + Text)
# Run: streamlit run main_enhanced.py
import base64
import io
import json
import os
import subprocess
import tempfile
import time
import traceback
from typing import Optional, Tuple, Dict, Any, List
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image
import hashlib
import re
# Optional imports
try:
    import requests
except ImportError:
    requests = None
try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    pytesseract = None
    OCR_AVAILABLE = False

# ----------------------
# Configuration
# ----------------------
OLLAMA_HTTP_URL = "http://localhost:11434/api/generate"
DEFAULT_TEXT_MODEL = "llama3:latest"
DEFAULT_IMAGE_MODEL = "llava:latest"

# Waste categories with detailed disposal information
CATEGORIES = {
    0: {
        "name": "Organic Waste",
        "icon": "🍃",
        "color": "#4CAF50",
        "disposal": "Compost or use green waste bin. Avoid plastic bags."
    },
    1: {
        "name": "Inorganic Waste",
        "icon": "🥤",
        "color": "#2196F3",
        "disposal": "Recycle if possible. Rinse containers before disposal."
    },
    2: {
        "name": "Hazardous Waste",
        "icon": "☣️",
        "color": "#F44336",
        "disposal": "Take to hazardous waste collection facility. Never mix with regular trash."
    },
    3: {
        "name": "Electronic Waste (E-Waste)",
        "icon": "📱",
        "color": "#9C27B0",
        "disposal": "Recycle at e-waste collection points. Remove batteries if possible."
    },
    4: {
        "name": "Construction & Demolition Waste",
        "icon": "🧱",
        "color": "#795548",
        "disposal": "Rent a dumpster or use construction waste collection service."
    },
    5: {
        "name": "Industrial Waste",
        "icon": "🏭",
        "color": "#607D8B",
        "disposal": "Follow industrial waste regulations. Contact waste management company."
    },
    6: {
        "name": "Biomedical Waste",
        "icon": "💉",
        "color": "#E91E63",
        "disposal": "Use puncture-proof containers. Return to medical facility or pharmacy."
    },
    7: {
        "name": "Radioactive Waste",
        "icon": "☢️",
        "color": "#FF9800",
        "disposal": "Contact specialized radioactive waste handlers. Follow strict protocols."
    },
    8: {
        "name": "Special - Textiles/Paper/Agricultural",
        "icon": "👕",
        "color": "#009688",
        "disposal": "Textiles: donate or recycle. Paper: recycle. Agricultural: compost if organic."
    },
    9: {
        "name": "Other/Unknown",
        "icon": "❓",
        "color": "#9E9E9E",
        "disposal": "Check local guidelines. When in doubt, contact waste management authority."
    }
}

# Enhanced disposal information for each category
DISPOSAL_INFO = {
    0: {  # Organic
        "steps": [
            "Collect all organic waste in a compostable container",
            "Remove any non-organic materials (plastic, metal)",
            "Chop large items into smaller pieces for faster decomposition",
            "Add to compost bin or green waste collection",
            "Cover with brown materials (leaves, paper) to reduce odor"
        ],
        "options": "Home compost bin, municipal green waste collection, community composting program",
        "prep": "Remove packaging, rinse if contaminated with non-organic materials",
        "safety": "Avoid composting meat, dairy, or diseased plants in home compost",
        "tips": [
            "Keep compost moist but not wet",
            "Turn compost regularly for aeration",
            "Balance green and brown materials",
            "Use compost in garden after 2-3 months",
            "Consider vermicomposting for apartment dwellers"
        ],
        "mistakes": [
            "Composting meat or dairy which attracts pests",
            "Adding diseased plants that can spread pathogens",
            "Not turning compost leading to anaerobic decomposition"
        ],
        "description": "Organic waste includes food scraps, yard trimmings, and other biodegradable materials that can be broken down by microorganisms.",
        "reason": "Organic waste is categorized separately because it can be composted and turned into nutrient-rich soil, reducing landfill waste.",
        "environmental_impact": "Proper composting of organic waste reduces methane emissions from landfills and creates valuable fertilizer for gardens and farms."
    },
    1: {  # Inorganic
        "steps": [
            "Empty contents completely and rinse container",
            "Remove caps, lids, and labels if possible",
            "Flatten items to save space in recycling bin",
            "Sort by material type (plastic, glass, metal)",
            "Place in appropriate recycling bin or take to recycling center"
        ],
        "options": "Curbside recycling, drop-off recycling centers, retailer take-back programs",
        "prep": "Clean thoroughly, remove non-recyclable parts, check local recycling codes",
        "safety": "Handle broken glass with care, wear gloves when handling sharp edges",
        "tips": [
            "Know your local recycling rules as they vary by location",
            "Rinse containers to prevent contamination",
            "Remove caps and lids as they may be different materials",
            "Flatten cardboard boxes to save space",
            "When in doubt, throw it out to avoid recycling contamination"
        ],
        "mistakes": [
            "Not rinsing containers causing contamination",
            "Recycling materials not accepted locally",
            "Including plastic bags in curbside recycling"
        ],
        "description": "Inorganic waste includes materials like plastic, glass, metal, and other non-biodegradable items that can often be recycled.",
        "reason": "Inorganic waste is categorized based on its recyclability and the need to separate it from organic waste to prevent contamination.",
        "environmental_impact": "Recycling inorganic materials conserves natural resources, reduces energy consumption, and decreases pollution from manufacturing new products."
    },
    2: {  # Hazardous
        "steps": [
            "Keep in original container if possible",
            "Seal tightly to prevent leaks",
            "Label clearly as hazardous waste",
            "Store in a cool, dry place away from children and pets",
            "Take to designated hazardous waste collection facility"
        ],
        "options": "Household hazardous waste collection events, permanent drop-off facilities, retailer take-back programs",
        "prep": "Never mix different hazardous materials, keep original labels",
        "safety": "Wear protective gear, ensure good ventilation, keep away from heat sources",
        "tips": [
            "Check local hazardous waste collection schedules",
            "Never pour down drains or toilets",
            "Store in original containers with labels intact",
            "Keep away from children and pets",
            "Use up completely before disposal when possible"
        ],
        "mistakes": [
            "Pouring hazardous chemicals down drains",
            "Mixing different hazardous materials",
            "Throwing in regular trash causing environmental harm"
        ],
        "description": "Hazardous waste includes materials that are toxic, flammable, corrosive, or reactive, such as batteries, paint, chemicals, and pesticides.",
        "reason": "Hazardous waste requires special handling because it can pose serious risks to human health and the environment if not disposed of properly.",
        "environmental_impact": "Improper disposal of hazardous waste can contaminate soil, water, and air, harming wildlife and ecosystems, and potentially causing long-term health problems in humans."
    },
    3: {  # E-Waste
        "steps": [
            "Back up and erase all personal data",
            "Remove batteries if possible",
            "Separate components by material type",
            "Bundle cables and accessories together",
            "Take to certified e-waste recycling facility"
        ],
        "options": "E-waste recycling centers, retailer take-back programs, manufacturer mail-back programs",
        "prep": "Delete personal data, remove batteries, separate accessories",
        "safety": "Unplug devices before disassembly, handle CRT monitors carefully",
        "tips": [
            "Consider donating working electronics",
            "Remove batteries before recycling",
            "Erase personal data completely",
            "Check for manufacturer recycling programs",
            "Look for certified e-waste recyclers"
        ],
        "mistakes": [
            "Not erasing personal data before recycling",
            "Throwing electronics in regular trash",
            "Including batteries with e-waste without removal"
        ],
        "description": "Electronic waste (e-waste) includes discarded electronic devices such as computers, phones, TVs, printers, and other electronic equipment.",
        "reason": "E-waste is categorized separately because it contains valuable materials that can be recycled, as well as hazardous components that require special handling.",
        "environmental_impact": "Proper e-waste recycling recovers valuable metals, reduces toxic substances in landfills, and prevents environmental contamination from heavy metals and other hazardous materials."
    },
    4: {  # Construction
        "steps": [
            "Sort materials by type (concrete, wood, metal, etc.)",
            "Remove hazardous materials (asbestos, lead paint)",
            "Clean materials to remove contamination",
            "Break down large items into manageable pieces",
            "Rent a dumpster or use construction waste collection service"
        ],
        "options": "Construction waste collection services, recycling facilities, landfill disposal",
        "prep": "Sort by material type, remove hazardous components, clean if contaminated",
        "safety": "Wear protective gear, be aware of hazardous materials, use proper lifting techniques",
        "tips": [
            "Salvage reusable materials for future projects",
            "Recycle metal, concrete, and wood when possible",
            "Hire professionals for hazardous material removal",
            "Plan waste management before starting project",
            "Consider deconstruction instead of demolition"
        ],
        "mistakes": [
            "Not sorting materials leading to unnecessary landfill use",
            "Improper handling of hazardous materials",
            "Overfilling dumpsters creating safety hazards"
        ],
        "description": "Construction and demolition waste includes materials generated from building, renovation, and demolition projects, such as concrete, wood, metal, and drywall.",
        "reason": "Construction waste is categorized separately due to its bulk, potential for recycling, and the presence of hazardous materials that may require special handling.",
        "environmental_impact": "Proper management of construction waste reduces landfill use, conserves resources through recycling, and prevents contamination from hazardous building materials."
    },
    5: {  # Industrial
        "steps": [
            "Identify waste type and composition",
            "Segregate hazardous from non-hazardous waste",
            "Document waste characteristics and origin",
            "Package according to regulatory requirements",
            "Contract with licensed industrial waste handler"
        ],
        "options": "Licensed industrial waste management companies, specialized treatment facilities",
        "prep": "Analyze waste composition, segregate by type, document properly",
        "safety": "Follow OSHA regulations, use proper PPE, train personnel on handling procedures",
        "tips": [
            "Conduct waste audit to identify reduction opportunities",
            "Explore recycling and reuse options",
            "Stay updated on waste regulations",
            "Implement waste minimization practices",
            "Maintain proper documentation for compliance"
        ],
        "mistakes": [
            "Not properly characterizing waste type",
            "Mixing incompatible waste materials",
            "Improper documentation leading to compliance issues"
        ],
        "description": "Industrial waste includes materials generated from manufacturing, industrial processes, and other commercial activities, which may include chemicals, byproducts, and other specialized waste.",
        "reason": "Industrial waste is categorized separately because it often requires specialized handling, treatment, and disposal methods due to its potential hazards and regulatory requirements.",
        "environmental_impact": "Proper industrial waste management prevents environmental contamination, ensures regulatory compliance, and can lead to resource recovery and waste reduction through recycling and treatment."
    },
    6: {  # Biomedical
        "steps": [
            "Place in puncture-proof biohazard container",
            "Seal container securely",
            "Label with biohazard symbol and contents",
            "Store in designated biomedical waste area",
            "Contact licensed biomedical waste disposal service"
        ],
        "options": "Licensed biomedical waste disposal companies, medical facilities, pharmacies",
        "prep": "Use approved containers, never overfill, keep containers closed",
        "safety": "Wear appropriate PPE, handle sharps carefully, follow exposure protocols",
        "tips": [
            "Never recap needles by hand",
            "Use safety-engineered sharps containers",
            "Train all personnel on proper handling",
            "Keep containers in designated areas only",
            "Report any exposures immediately"
        ],
        "mistakes": [
            "Not using proper biohazard containers",
            "Overfilling containers creating safety risks",
            "Improper sharps handling causing needlestick injuries"
        ],
        "description": "Biomedical waste includes any waste that contains infectious materials or potentially infectious substances, such as used needles, bandages, blood products, and other medical waste.",
        "reason": "Biomedical waste is categorized separately because it poses specific health risks and requires special handling, treatment, and disposal methods to prevent infection and contamination.",
        "environmental_impact": "Proper biomedical waste disposal prevents the spread of infectious diseases, protects healthcare workers and the public, and ensures safe treatment and destruction of potentially hazardous materials."
    },
    7: {  # Radioactive
        "steps": [
            "Isolate in designated radioactive waste container",
            "Label with radiation symbol and isotope information",
            "Document activity level and half-life",
            "Store in secure, shielded location",
            "Contact licensed radioactive waste handler"
        ],
        "options": "Licensed radioactive waste disposal facilities, specialized handlers",
        "prep": "Identify isotope and activity level, use appropriate shielding",
        "safety": "Follow radiation safety protocols, minimize exposure time, use shielding",
        "tips": [
            "Monitor radiation levels regularly",
            "Follow ALARA principles (As Low As Reasonably Achievable)",
            "Maintain detailed records",
            "Train personnel on radiation safety",
            "Have emergency procedures in place"
        ],
        "mistakes": [
            "Not properly identifying radioactive materials",
            "Improper storage leading to exposure risks",
            "Not following regulatory requirements"
        ],
        "description": "Radioactive waste contains radioactive materials that emit ionizing radiation, including materials from nuclear power plants, medical facilities, and industrial applications.",
        "reason": "Radioactive waste is categorized separately because it requires specialized handling, storage, and disposal methods to protect human health and the environment from radiation exposure.",
        "environmental_impact": "Proper radioactive waste management prevents radiation exposure, protects ecosystems, and ensures long-term containment of radioactive materials to prevent environmental contamination."
    },
    8: {  # Special
        "steps": [
            "Sort items by material type (textiles, paper, agricultural)",
            "Clean items if soiled or contaminated",
            "Prepare for appropriate disposal method",
            "Package according to material requirements",
            "Take to appropriate collection point"
        ],
        "options": "Textile recycling bins, paper recycling, agricultural waste collection",
        "prep": "Clean items, remove non-recyclable components, sort by material",
        "safety": "Handle agricultural chemicals with care, wear gloves when handling soiled textiles",
        "tips": [
            "Donate usable clothing and textiles",
            "Compost clean paper products",
            "Recycle agricultural plastics when possible",
            "Reuse paper for crafts or note-taking",
            "Properly dispose of pesticide containers"
        ],
        "mistakes": [
            "Not sorting materials properly",
            "Including contaminated items in recycling",
            "Not cleaning items before recycling"
        ],
        "description": "Special waste includes textiles, paper, agricultural waste, and other materials that don't fit neatly into other categories but have specific disposal requirements.",
        "reason": "Special waste is categorized separately because these materials often have unique recycling or disposal options that differ from general waste streams.",
        "environmental_impact": "Proper management of special waste materials promotes recycling, reduces landfill use, and ensures that materials are processed in the most environmentally friendly way possible."
    },
    9: {  # Other/Unknown
        "steps": [
            "Research the item's composition online",
            "Contact local waste management authority",
            "Check manufacturer's disposal recommendations",
            "If unsure, treat as general waste",
            "Document for future reference"
        ],
        "options": "General waste collection, local waste management authority, manufacturer guidance",
        "prep": "Clean the item, remove any hazardous components if identifiable",
        "safety": "Handle with care if composition is unknown, wear gloves",
        "tips": [
            "Take a photo and search online for disposal guidance",
            "Call your local waste management hotline",
            "Check if the manufacturer has a take-back program",
            "When in doubt, dispose in general waste",
            "Consider if the item can be repurposed"
        ],
        "mistakes": [
            "Assuming unknown items are recyclable",
            "Mixing unknown items with hazardous waste",
            "Not researching proper disposal methods"
        ],
        "description": "Other/Unknown waste includes items that don't clearly fit into other categories or whose composition is uncertain, requiring special consideration for proper disposal.",
        "reason": "This category exists for items that are difficult to classify, ensuring they receive appropriate attention rather than being improperly disposed of in general waste.",
        "environmental_impact": "Proper handling of unknown waste prevents environmental contamination and ensures that potentially hazardous materials are not mixed with general waste streams."
    }
}

# ----------------------
# Helper Functions
# ----------------------
def _log(msg: str):
    """Log messages to session state for debugging"""
    try:
        if "logs" not in st.session_state:
            st.session_state["logs"] = []
        timestamp = time.strftime('%H:%M:%S')
        st.session_state["logs"].append(f"[{timestamp}] {msg}")
        # Keep only last 100 logs
        st.session_state["logs"] = st.session_state["logs"][-100:]
    except Exception:
        pass

def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Extract and parse JSON from text response"""
    if not text:
        return None
    
    # Try to find JSON block
    start = text.find("{")
    if start == -1:
        return None
    
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                json_str = text[start:i+1]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    continue
    return None

def get_content_hash(content: bytes) -> str:
    """Generate hash for content to enable caching"""
    return hashlib.md5(content).hexdigest()

def get_category_details(category_id: int) -> Dict[str, Any]:
    """Get detailed information about a waste category"""
    category = CATEGORIES.get(category_id, CATEGORIES[9])
    info = DISPOSAL_INFO.get(category_id, DISPOSAL_INFO[9])
    
    return {
        "category_id": category_id,
        "category_name": category["name"],
        "description": info["description"],
        "reason": info["reason"],
        "disposal_steps": info["steps"],
        "environmental_impact": info["environmental_impact"],
        "common_mistakes": info["mistakes"],
        "additional_tips": info["tips"],
        "local_disposal_options": info["options"],
        "preparation_requirements": info["prep"],
        "safety_precautions": info["safety"],
        "confidence": 1.0
    }

def format_disposal_info(details: Dict[str, Any]) -> str:
    """Format disposal information for chat display"""
    category_id = details.get("category_id", 9)
    category = CATEGORIES.get(category_id, CATEGORIES[9])
    
    # Build disposal steps list with proper HTML
    steps_html = ""
    for step in details.get("disposal_steps", []):
        steps_html += f"                <li>{step}</li>\n"
    
    # Build tips list with proper HTML
    tips_html = ""
    for tip in details.get("additional_tips", []):
        tips_html += f"                <li>{tip}</li>\n"
    
    # Build mistakes list with proper HTML
    mistakes_html = ""
    for mistake in details.get("common_mistakes", []):
        mistakes_html += f"                <li>{mistake}</li>\n"
    
    formatted_info = f"""<div style="
        background: linear-gradient(135deg, {category['color']}22, {category['color']}11);
        border: 1px solid {category['color']}44;
        border-radius: 12px;
        padding: 15px;
        margin: 10px 0;
    ">
        <div style="display: flex; align-items: center; margin-bottom: 10px;">
            <span style="font-size: 1.8rem; margin-right: 10px;">{category['icon']}</span>
            <div>
                <h4 style="margin: 0; color: {category['color']}; font-weight: bold;">{details.get('category_name', 'Unknown Waste')}</h4>
            </div>
        </div>
        
        <div style="margin-top: 15px;">
            <h5 style="color: #93c5fd; margin-top: 0; margin-bottom: 8px;">🔍 Description</h5>
            <p style="margin: 0; line-height: 1.5;">{details.get('description', 'No description available.')}</p>
        </div>
        
        <div style="margin-top: 15px;">
            <h5 style="color: #10b981; margin-top: 0; margin-bottom: 8px;">♻️ How to Dispose Properly</h5>
            <ol style="margin: 0; padding-left: 20px; line-height: 1.6;">
{steps_html}            </ol>
        </div>
        
        <div style="margin-top: 15px;">
            <h5 style="color: #fcd34d; margin-top: 0; margin-bottom: 8px;">💡 Tips for Handling</h5>
            <ul style="margin: 0; padding-left: 20px; line-height: 1.6;">
{tips_html}            </ul>
        </div>
        
        <div style="margin-top: 15px;">
            <h5 style="color: #fca5a5; margin-top: 0; margin-bottom: 8px;">⚠️ Common Mistakes to Avoid</h5>
            <ul style="margin: 0; padding-left: 20px; line-height: 1.6;">
{mistakes_html}            </ul>
        </div>
        
        <div style="margin-top: 15px;">
            <h5 style="color: #93c5fd; margin-top: 0; margin-bottom: 8px;">📍 Where to Take It</h5>
            <p style="margin: 0; line-height: 1.5;">{details.get('local_disposal_options', 'Check local guidelines.')}</p>
        </div>
        
        <div style="margin-top: 15px;">
            <h5 style="color: #f59e0b; margin-top: 0; margin-bottom: 8px;">⚠️ Safety Precautions</h5>
            <p style="margin: 0; line-height: 1.5;">{details.get('safety_precautions', 'Handle with care.')}</p>
        </div>
    </div>"""
    
    return formatted_info

# ----------------------
# Ollama Integration
# ----------------------
def query_ollama(
    model: str,
    prompt: str,
    image_bytes: Optional[bytes] = None,
    max_tokens: int = 1024,
    temperature: float = 0.0,
    timeout: int = 15,
) -> Optional[Dict[str, Any]]:
    """Query Ollama model with fallback mechanisms"""
    _log(f"Querying {model} with prompt length: {len(prompt)}")
    
    # Try HTTP first
    if requests is not None:
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False
            }
            
            if image_bytes:
                payload["images"] = [base64.b64encode(image_bytes).decode("utf-8")]
            
            _log("Attempting HTTP request")
            response = requests.post(
                OLLAMA_HTTP_URL,
                json=payload,
                timeout=timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                _log("HTTP request successful")
                return result
            else:
                _log(f"HTTP request failed: {response.status_code}")
        except Exception as e:
            _log(f"HTTP error: {str(e)}")
    
    # Fallback to CLI
    img_path = None
    tmp_path = None
    try:
        _log("Attempting CLI fallback")
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp_file:
            if image_bytes:
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as img_file:
                    img_file.write(image_bytes)
                    img_path = img_file.name
                tmp_file.write(f"[IMAGE]{img_path}[/IMAGE]\n")
            tmp_file.write(prompt)
            tmp_path = tmp_file.name
        
        result = subprocess.run(
            ["ollama", "run", model],
            input=open(tmp_path, 'rb').read(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout
        )
        
        if result.returncode == 0:
            output = result.stdout.decode('utf-8', errors='ignore')
            _log("CLI request successful")
            return {"response": output}
        else:
            _log(f"CLI failed with code: {result.returncode}")
    except Exception as e:
        _log(f"CLI error: {str(e)}")
    finally:
        # Clean up temp files
        for path in [tmp_path, img_path] if img_path else [tmp_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
    
    return None

# ----------------------
# Heuristic Classification
# ----------------------
def heuristic_classify(text: str) -> Tuple[int, str, str, float, Dict[str, Any]]:
    """Classify waste using heuristic rules with enhanced disposal information"""
    text_lower = text.lower()
    
    # Define category keywords with confidence scores
    category_keywords = {
        0: [  # Organic
            ("food scrap", 0.95), ("fruit peel", 0.95), ("vegetable", 0.9),
            ("leftover", 0.85), ("coffee ground", 0.9), ("tea bag", 0.9),
            ("yard waste", 0.85), ("grass clipping", 0.9), ("leaf", 0.85),
            ("wood chip", 0.8), ("sawdust", 0.8), ("manure", 0.95)
        ],
        1: [  # Inorganic
            ("plastic bottle", 0.95), ("plastic bag", 0.9), ("glass jar", 0.95),
            ("metal can", 0.95), ("aluminum foil", 0.9), ("styrofoam", 0.85),
            ("ceramic", 0.8), ("rubber", 0.85), ("pvc", 0.9)
        ],
        2: [  # Hazardous
            ("battery", 0.95), ("paint", 0.95), ("pesticide", 0.95),
            ("cleaning chemical", 0.9), ("motor oil", 0.95), ("fluorescent bulb", 0.9),
            ("asbestos", 0.99), ("bleach", 0.9), ("ammonia", 0.9)
        ],
        3: [  # E-Waste
            ("phone", 0.95), ("computer", 0.95), ("tv", 0.95),
            ("printer", 0.9), ("monitor", 0.95), ("cable", 0.85),
            ("charger", 0.9), ("keyboard", 0.85), ("mouse", 0.85)
        ],
        4: [  # Construction
            ("concrete", 0.95), ("brick", 0.95), ("drywall", 0.9),
            ("tile", 0.9), ("asphalt", 0.9), ("lumber", 0.85),
            ("insulation", 0.85), ("roofing", 0.85)
        ],
        5: [  # Industrial
            ("slag", 0.95), ("industrial waste", 0.9), ("chemical waste", 0.95),
            ("manufacturing byproduct", 0.9), ("factory waste", 0.85)
        ],
        6: [  # Biomedical
            ("syringe", 0.99), ("needle", 0.99), ("bandage", 0.95),
            ("gauze", 0.95), ("blood product", 0.99), ("glove", 0.85),
            ("mask", 0.8), ("vial", 0.9), ("iv bag", 0.95)
        ],
        7: [  # Radioactive
            ("radioactive", 0.99), ("uranium", 0.99), ("plutonium", 0.99),
            ("radiation source", 0.99), ("nuclear waste", 0.99)
        ],
        8: [  # Special
            ("textile", 0.9), ("clothing", 0.9), ("paper", 0.85),
            ("cardboard", 0.85), ("agricultural film", 0.9), ("pesticide container", 0.95)
        ]
    }
    
    # Find best matching category
    best_category = 9  # Default to "Other"
    best_confidence = 0.0
    
    for category_id, keywords in category_keywords.items():
        for keyword, confidence in keywords:
            if keyword in text_lower:
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_category = category_id
    
    # Get category details
    return best_category, CATEGORIES[best_category]["name"], DISPOSAL_INFO[best_category]["description"], best_confidence, get_category_details(best_category)

# ----------------------
# Image Processing
# ----------------------
def preprocess_image(image_bytes: bytes, max_size: int = 1024) -> bytes:
    """Preprocess image for optimal model input"""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize if too large
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.LANCZOS)
        
        # Save to buffer
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=85)
        return buffer.getvalue()
    except Exception as e:
        _log(f"Image preprocessing error: {str(e)}")
        return image_bytes

def extract_text_from_image(image_bytes: bytes) -> str:
    """Extract text from image using OCR"""
    if not OCR_AVAILABLE:
        return ""
    
    try:
        img = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(img, config='--psm 6')
        return " ".join(text.split())
    except Exception as e:
        _log(f"OCR error: {str(e)}")
        return ""

# ----------------------
# Classification Prompts
# ----------------------
def build_image_prompt(caption: str) -> str:
    """Build prompt for image classification with enhanced disposal details"""
    categories_str = ", ".join([f"{k}: {v['name']}" for k, v in CATEGORIES.items()])
    
    return f"""
You are a waste classification expert. Analyze the following image caption and classify the waste.
Categories: {categories_str}
Instructions:
1. Provide a comprehensive response about this waste item including:
   - Detailed description of the waste
   - Why it belongs to this category
   - Step-by-step disposal instructions (at least 5 detailed steps)
   - Environmental impact of proper disposal
   - Common mistakes to avoid (at least 3 specific mistakes)
   - Additional tips for responsible disposal (at least 5 practical tips)
   - Local disposal options (where to take it)
   - Preparation requirements (cleaning, disassembly, etc.)
   - Safety precautions if applicable
2. Respond with only a JSON object
3. Use the category_id that best matches the waste type
4. Include a confidence score (0.0-1.0)
Image Caption: "{caption}"
Response format:
{{
    "category_id": <int>,
    "category_name": "<string>",
    "description": "<string>",
    "reason": "<string>",
    "disposal_steps": ["<string>", "<string>", ...],
    "environmental_impact": "<string>",
    "common_mistakes": ["<string>", "<string>", ...],
    "additional_tips": ["<string>", "<string>", ...],
    "local_disposal_options": "<string>",
    "preparation_requirements": "<string>",
    "safety_precautions": "<string>",
    "confidence": <float>
}}
"""

def build_text_prompt(text: str) -> str:
    """Build prompt for text classification with enhanced disposal details"""
    categories_str = ", ".join([f"{k}: {v['name']}" for k, v in CATEGORIES.items()])
    
    return f"""
You are a waste classification expert. Analyze the following description and classify the waste.
Categories: {categories_str}
Instructions:
1. Provide a comprehensive response about this waste item including:
   - Detailed description of the waste
   - Why it belongs to this category
   - Step-by-step disposal instructions (at least 5 detailed steps)
   - Environmental impact of proper disposal
   - Common mistakes to avoid (at least 3 specific mistakes)
   - Additional tips for responsible disposal (at least 5 practical tips)
   - Local disposal options (where to take it)
   - Preparation requirements (cleaning, disassembly, etc.)
   - Safety precautions if applicable
2. Respond with only a JSON object
3. Use the category_id that best matches the waste type
4. Include a confidence score (0.0-1.0)
Description: "{text}"
Response format:
{{
    "category_id": <int>,
    "category_name": "<string>",
    "description": "<string>",
    "reason": "<string>",
    "disposal_steps": ["<string>", "<string>", ...],
    "environmental_impact": "<string>",
    "common_mistakes": ["<string>", "<string>", ...],
    "additional_tips": ["<string>", "<string>", ...],
    "local_disposal_options": "<string>",
    "preparation_requirements": "<string>",
    "safety_precautions": "<string>",
    "confidence": <float>
}}
"""

# ----------------------
# Main Classification Functions
# ----------------------
def classify_image(image_bytes: bytes, image_model: str, text_model: str) -> Tuple[int, str, str, float, Dict[str, Any]]:
    """Classify waste from image"""
    _log("Starting image classification")
    
    # Preprocess image
    processed_img = preprocess_image(image_bytes)
    img_hash = get_content_hash(processed_img)
    
    # Check cache
    if "image_cache" not in st.session_state:
        st.session_state.image_cache = {}
    
    if img_hash in st.session_state.image_cache:
        _log("Using cached image classification")
        return st.session_state.image_cache[img_hash]
    
    # Extract text from image
    ocr_text = extract_text_from_image(processed_img)
    _log(f"OCR extracted: {ocr_text[:50]}...")
    
    # Generate image caption
    caption_prompt = "Describe this image in one short sentence (3-8 words). Return only the caption."
    caption_result = query_ollama(image_model, caption_prompt, image_bytes=processed_img)
    
    if caption_result and "response" in caption_result:
        caption = caption_result["response"].strip().split('\n')[0]
    else:
        caption = ocr_text[:100] if ocr_text else "an object"
    
    _log(f"Generated caption: {caption}")
    
    # Classify based on caption
    classify_prompt = build_image_prompt(caption)
    classify_result = query_ollama(text_model, classify_prompt)
    
    if classify_result and "response" in classify_result:
        parsed = extract_json_from_text(classify_result["response"])
        if parsed:
            result = (
                int(parsed.get("category_id", 9)),
                parsed.get("category_name", CATEGORIES[9]["name"]),
                parsed.get("description", ""),
                float(parsed.get("confidence", 0.5)),
                parsed
            )
            # Cache result
            st.session_state.image_cache[img_hash] = result
            _log("Image classification successful")
            return result
    
    # Fallback to heuristic classification
    _log("Using heuristic fallback for image")
    return heuristic_classify(caption)

def classify_text(text: str, model: str) -> Tuple[int, str, str, float, Dict[str, Any]]:
    """Classify waste from text description"""
    _log("Starting text classification")
    
    # Check cache
    text_hash = hashlib.md5(text.encode()).hexdigest()
    if "text_cache" not in st.session_state:
        st.session_state.text_cache = {}
    
    if text_hash in st.session_state.text_cache:
        _log("Using cached text classification")
        return st.session_state.text_cache[text_hash]
    
    # Build prompt and query model
    prompt = build_text_prompt(text)
    result = query_ollama(model, prompt)
    
    if result and "response" in result:
        parsed = extract_json_from_text(result["response"])
        if parsed:
            classification = (
                int(parsed.get("category_id", 9)),
                parsed.get("category_name", CATEGORIES[9]["name"]),
                parsed.get("description", ""),
                float(parsed.get("confidence", 0.5)),
                parsed
            )
            # Cache result
            st.session_state.text_cache[text_hash] = classification
            _log("Text classification successful")
            return classification
    
    # Fallback to heuristic classification
    _log("Using heuristic fallback for text")
    return heuristic_classify(text)

# ----------------------
# UI Components
# ----------------------
def render_result(category_id: int, category_name: str, description: str, reason: str, confidence: float, details: Dict[str, Any]):
    """Render classification result with enhanced UI and detailed information"""
    category = CATEGORIES.get(category_id, CATEGORIES[9])
    
    # Create main result card
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {category['color']}22, {category['color']}11);
        border: 1px solid {category['color']}44;
        border-radius: 12px;
        padding: 20px;
        margin: 15px 0;
    ">
        <div style="display: flex; align-items: center; margin-bottom: 15px;">
            <span style="font-size: 2.5rem; margin-right: 15px;">{category['icon']}</span>
            <div>
                <h3 style="margin: 0; color: {category['color']}; font-weight: bold;">{category_name}</h3>
                <p style="margin: 0; opacity: 0.8; font-weight: 500;">Confidence: {confidence:.0%}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Detailed description section
    st.markdown("""
    <div style="
        background: #1f2937;
        border: 2px solid #374151;
        border-radius: 12px;
        padding: 20px;
        margin: 15px 0;
    ">
        <h4 style="margin-top: 0; color: #93c5fd; font-weight: 600; font-size: 1.2rem;">📋 Detailed Analysis</h4>
    """, unsafe_allow_html=True)
    
    # Description
    st.markdown(f"""
    <div style="
        background: rgba(0,0,0,0.2);
        padding: 12px 16px;
        border-radius: 8px;
        margin: 8px 0;
        border-left: 3px solid #3b82f6;
        color: #f0f9ff;
        line-height: 1.5;
    ">
        <strong>🔍 Description:</strong> {description}
    </div>
    """, unsafe_allow_html=True)
    
    # Reason
    st.markdown(f"""
    <div style="
        background: rgba(0,0,0,0.2);
        padding: 12px 16px;
        border-radius: 8px;
        margin: 8px 0;
        border-left: 3px solid #3b82f6;
        color: #f0f9ff;
        line-height: 1.5;
    ">
        <strong>🏷️ Classification Reason:</strong> {reason}
    </div>
    """, unsafe_allow_html=True)
    
    # Local disposal options
    if details.get("local_disposal_options"):
        st.markdown(f"""
        <div style="
            background: rgba(0,0,0,0.2);
            padding: 12px 16px;
            border-radius: 8px;
            margin: 8px 0;
            border-left: 3px solid #10b981;
            color: #f0fdf4;
            line-height: 1.5;
        ">
            <strong>📍 Where to Take It:</strong> {details.get("local_disposal_options")}
        </div>
        """, unsafe_allow_html=True)
    
    # Preparation requirements
    if details.get("preparation_requirements"):
        st.markdown(f"""
        <div style="
            background: rgba(0,0,0,0.2);
            padding: 12px 16px;
            border-radius: 8px;
            margin: 8px 0;
            border-left: 3px solid #10b981;
            color: #f0fdf4;
            line-height: 1.5;
        ">
            <strong>🛠️ Preparation Required:</strong> {details.get("preparation_requirements")}
        </div>
        """, unsafe_allow_html=True)
    
    # Safety precautions
    if details.get("safety_precautions"):
        st.markdown(f"""
        <div style="
            background: rgba(0,0,0,0.2);
            padding: 12px 16px;
            border-radius: 8px;
            margin: 8px 0;
            border-left: 3px solid #f59e0b;
            color: #fefce8;
            line-height: 1.5;
        ">
            <strong>⚠️ Safety Precautions:</strong> {details.get("safety_precautions")}
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Disposal steps section
    st.markdown("""
    <div style="
        background: #1f2937;
        border: 2px solid #374151;
        border-radius: 12px;
        padding: 20px;
        margin: 15px 0;
    ">
        <h4 style="margin-top: 0; color: #10b981; font-weight: 600; font-size: 1.2rem;">♻️ Step-by-Step Disposal Instructions</h4>
    """, unsafe_allow_html=True)
    
    for i, step in enumerate(details.get("disposal_steps", []), 1):
        st.markdown(f"""
        <div style="
            background: rgba(0,0,0,0.2);
            padding: 12px 16px;
            border-radius: 8px;
            margin: 8px 0;
            border-left: 3px solid #10b981;
            color: #f0fdf4;
            line-height: 1.5;
        ">
            <strong>Step {i}:</strong> {step}
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Environmental impact
    st.markdown(f"""
    <div style="
        background: #1f2937;
        border: 2px solid #374151;
        border-radius: 12px;
        padding: 20px;
        margin: 15px 0;
    ">
        <h4 style="margin-top: 0; color: #10b981; font-weight: 600; font-size: 1.2rem;">🌍 Environmental Impact</h4>
        <div style="
            background: rgba(0,0,0,0.2);
            padding: 12px 16px;
            border-radius: 8px;
            margin: 8px 0;
            border-left: 3px solid #10b981;
            color: #f0fdf4;
            line-height: 1.5;
        ">
            {details.get("environmental_impact", "Proper disposal helps reduce environmental impact and conserve resources.")}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Common mistakes
    st.markdown("""
    <div style="
        background: #1f2937;
        border: 2px solid #374151;
        border-radius: 12px;
        padding: 20px;
        margin: 15px 0;
    ">
        <h4 style="margin-top: 0; color: #fca5a5; font-weight: 600; font-size: 1.2rem;">⚠️ Common Mistakes to Avoid</h4>
    """, unsafe_allow_html=True)
    
    for mistake in details.get("common_mistakes", []):
        st.markdown(f"""
        <div style="
            background: rgba(0,0,0,0.2);
            padding: 12px 16px;
            border-radius: 8px;
            margin: 8px 0;
            border-left: 3px solid #ef4444;
            color: #fef2f2;
            line-height: 1.5;
        ">
            <strong>❌</strong> {mistake}
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Additional tips
    st.markdown("""
    <div style="
        background: #1f2937;
        border: 2px solid #374151;
        border-radius: 12px;
        padding: 20px;
        margin: 15px 0;
    ">
        <h4 style="margin-top: 0; color: #fcd34d; font-weight: 600; font-size: 1.2rem;">💡 Pro Tips for Responsible Disposal</h4>
    """, unsafe_allow_html=True)
    
    for tip in details.get("additional_tips", []):
        st.markdown(f"""
        <div style="
            background: rgba(0,0,0,0.2);
            padding: 12px 16px;
            border-radius: 8px;
            margin: 8px 0;
            border-left: 3px solid #f59e0b;
            color: #fefce8;
            line-height: 1.5;
        ">
            <strong>✓</strong> {tip}
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Special warnings for hazardous waste
    if category_id in [2, 6, 7]:  # Hazardous, Biomedical, Radioactive
        st.markdown(f"""
        <div style="
            background: #7f1d1d;
            color: #fef2f2;
            padding: 15px;
            border-radius: 10px;
            margin: 10px 0;
            border-left: 5px solid {category['color']};
        ">
            <strong>⚠️ Special Handling Required!</strong><br>
            This waste requires special disposal procedures. Please follow local regulations and contact appropriate authorities.
        </div>
        """, unsafe_allow_html=True)
    
    # Call to action
    st.markdown("""
    <div style="
        background: rgba(99, 102, 241, 0.1);
        border: 1px solid rgba(99, 102, 241, 0.3);
        border-radius: 12px;
        padding: 15px;
        margin: 15px 0;
        text-align: center;
    ">
        <p style="margin: 0; color: #a5b4fc; font-weight: 600; font-size: 1.1rem;">
            🌟 Thank you for disposing responsibly! Every small action helps protect our environment.
        </p>
    </div>
    """, unsafe_allow_html=True)

def render_disposal_info_card(details: Dict[str, Any], timestamp: str):
    """Render disposal information using Streamlit components instead of HTML"""
    category_id = details.get("category_id", 9)
    category = CATEGORIES.get(category_id, CATEGORIES[9])
    
    # Create main card with category info
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {category['color']}22, {category['color']}11);
        border: 1px solid {category['color']}44;
        border-radius: 12px;
        padding: 15px;
        margin: 10px 0;
    ">
        <div style="display: flex; align-items: center; margin-bottom: 10px;">
            <span style="font-size: 1.8rem; margin-right: 10px;">{category['icon']}</span>
            <div>
                <h4 style="margin: 0; color: {category['color']}; font-weight: bold;">{details.get('category_name', 'Unknown Waste')}</h4>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Description section
    with st.expander("🔍 Description", expanded=True):
        st.markdown(f"""
        <div style="
            background: rgba(0,0,0,0.1);
            padding: 12px 16px;
            border-radius: 8px;
            margin: 5px 0;
            border-left: 3px solid #3b82f6;
            color: #f0f9ff;
            line-height: 1.5;
        ">
            {details.get('description', 'No description available.')}
        </div>
        """, unsafe_allow_html=True)
    
    # Disposal steps section
    with st.expander("♻️ How to Dispose Properly", expanded=True):
        for i, step in enumerate(details.get("disposal_steps", []), 1):
            st.markdown(f"""
            <div style="
                background: rgba(0,0,0,0.1);
                padding: 10px 16px;
                border-radius: 8px;
                margin: 5px 0;
                border-left: 3px solid #10b981;
                color: #f0fdf4;
                line-height: 1.5;
            ">
                <strong>Step {i}:</strong> {step}
            </div>
            """, unsafe_allow_html=True)
    
    # Tips section
    with st.expander("💡 Tips for Handling", expanded=True):
        for tip in details.get("additional_tips", []):
            st.markdown(f"""
            <div style="
                background: rgba(0,0,0,0.1);
                padding: 10px 16px;
                border-radius: 8px;
                margin: 5px 0;
                border-left: 3px solid #f59e0b;
                color: #fefce8;
                line-height: 1.5;
            ">
                <strong>✓</strong> {tip}
            </div>
            """, unsafe_allow_html=True)
    
    # Common mistakes section
    with st.expander("⚠️ Common Mistakes to Avoid", expanded=True):
        for mistake in details.get("common_mistakes", []):
            st.markdown(f"""
            <div style="
                background: rgba(0,0,0,0.1);
                padding: 10px 16px;
                border-radius: 8px;
                margin: 5px 0;
                border-left: 3px solid #ef4444;
                color: #fef2f2;
                line-height: 1.5;
            ">
                <strong>❌</strong> {mistake}
            </div>
            """, unsafe_allow_html=True)
    
    # Where to take it section
    with st.expander("📍 Where to Take It", expanded=True):
        st.markdown(f"""
        <div style="
            background: rgba(0,0,0,0.1);
            padding: 12px 16px;
            border-radius: 8px;
            margin: 5px 0;
            border-left: 3px solid #10b981;
            color: #f0fdf4;
            line-height: 1.5;
        ">
            {details.get('local_disposal_options', 'Check local guidelines.')}
        </div>
        """, unsafe_allow_html=True)
    
    # Safety precautions section
    with st.expander("⚠️ Safety Precautions", expanded=True):
        st.markdown(f"""
        <div style="
            background: rgba(0,0,0,0.1);
            padding: 12px 16px;
            border-radius: 8px;
            margin: 5px 0;
            border-left: 3px solid #f59e0b;
            color: #fefce8;
            line-height: 1.5;
        ">
            {details.get('safety_precautions', 'Handle with care.')}
        </div>
        """, unsafe_allow_html=True)
    
    # Environmental impact section
    with st.expander("🌍 Environmental Impact", expanded=True):
        st.markdown(f"""
        <div style="
            background: rgba(0,0,0,0.1);
            padding: 12px 16px;
            border-radius: 8px;
            margin: 5px 0;
            border-left: 3px solid #10b981;
            color: #f0fdf4;
            line-height: 1.5;
        ">
            {details.get("environmental_impact", "Proper disposal helps reduce environmental impact and conserve resources.")}
        </div>
        """, unsafe_allow_html=True)
    
    # Special warnings for hazardous waste
    if category_id in [2, 6, 7]:  # Hazardous, Biomedical, Radioactive
        st.markdown(f"""
        <div style="
            background: #7f1d1d;
            color: #fef2f2;
            padding: 15px;
            border-radius: 10px;
            margin: 10px 0;
            border-left: 5px solid {category['color']};
        ">
            <strong>⚠️ Special Handling Required!</strong><br>
            This waste requires special disposal procedures. Please follow local regulations and contact appropriate authorities.
        </div>
        """, unsafe_allow_html=True)
    
    # Timestamp
    st.markdown(f"""
    <div style="
        text-align: right; 
        font-size: 0.8rem; 
        opacity: 0.7; 
        margin-top: 10px; 
        margin-bottom: 15px;
        color: #9ca3af;
    ">
        {timestamp}
    </div>
    """, unsafe_allow_html=True)

def render_chat_history():
    """Render chat history with improved styling"""
    for i, msg in enumerate(st.session_state.chat_history):
        role = msg.get("role", "assistant")
        content = msg.get("text", "")
        timestamp = time.strftime('%H:%M', time.localtime(msg.get("time", time.time())))
        
        if role == "user":
            st.markdown(f"""
            <div style="text-align: right; margin: 10px 0;">
                <div style="
                    background: linear-gradient(90deg, #1e3a8a, #3b82f6);
                    color: white;
                    padding: 14px 20px;
                    border-radius: 18px;
                    display: inline-block;
                    max-width: 70%;
                    text-align: left;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.15);
                    font-weight: 500;
                ">
                    {content}
                    <div style="font-size: 0.8rem; opacity: 0.8; margin-top: 5px;">{timestamp}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Check if this is a classification result
            if content.startswith("I've classified this as"):
                # Extract the details from the previous message
                if i > 0 and st.session_state.chat_history[i-1]["role"] == "user":
                    user_input = st.session_state.chat_history[i-1]["text"]
                    # This is a classification result, render it differently
                    st.markdown(f"""
                    <div style="margin: 10px 0;">
                        <div style="
                            background: #374151;
                            color: #f9fafb;
                            padding: 14px 20px;
                            border-radius: 18px;
                            display: inline-block;
                            max-width: 70%;
                            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
                            border: 1px solid #4b5563;
                            font-weight: 500;
                            line-height: 1.5;
                        ">
                            {content}
                            <div style="font-size: 0.8rem; opacity: 0.7; margin-top: 5px;">{timestamp}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            # Check if this is a disposal info marker
            elif content.startswith("DISPOSAL_INFO:"):
                try:
                    category_id = int(content.split(":")[1])
                    details = get_category_details(category_id)
                    render_disposal_info_card(details, timestamp)
                except Exception:
                    # Fallback to regular text message
                    st.markdown(f"""
                    <div style="margin: 10px 0;">
                        <div style="
                            background: #374151;
                            color: #f9fafb;
                            padding: 14px 20px;
                            border-radius: 18px;
                            display: inline-block;
                            max-width: 70%;
                            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
                            border: 1px solid #4b5563;
                            font-weight: 500;
                            line-height: 1.5;
                        ">
                            Error loading disposal information
                            <div style="font-size: 0.8rem; opacity: 0.7; margin-top: 5px;">{timestamp}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            # Check if this is an HTML message (disposal info)
            elif content.startswith("<div style=") and "background: linear-gradient" in content:
                # Parse the details from the HTML content
                try:
                    # Extract category_id from the HTML (this is a hacky way)
                    category_match = re.search(r"category_id': (\d+)", content)
                    if category_match:
                        category_id = int(category_match.group(1))
                        details = get_category_details(category_id)
                        render_disposal_info_card(details, timestamp)
                except Exception:
                    # Fallback to regular HTML rendering
                    st.markdown(content, unsafe_allow_html=True)
                    st.markdown(f"""
                    <div style="
                        text-align: right; 
                        font-size: 0.8rem; 
                        opacity: 0.7; 
                        margin-top: 5px; 
                        margin-bottom: 15px;
                        color: #9ca3af;
                    ">
                        {timestamp}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                # Regular text message
                st.markdown(f"""
                <div style="margin: 10px 0;">
                    <div style="
                        background: #374151;
                        color: #f9fafb;
                        padding: 14px 20px;
                        border-radius: 18px;
                        display: inline-block;
                        max-width: 70%;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
                        border: 1px solid #4b5563;
                        font-weight: 500;
                        line-height: 1.5;
                    ">
                        {content}
                        <div style="font-size: 0.8rem; opacity: 0.7; margin-top: 5px;">{timestamp}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

# ----------------------
# Main Application
# ----------------------
def main():
    # Configure page
    st.set_page_config(
        page_title="Enhanced Waste Sorter",
        page_icon="♻️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS with dark theme for maximum contrast
    st.markdown("""
    <style>
        /* Main background and text colors */
        .stApp {
            background: #111827;
            color: #f9fafb;
        }
        
        /* Header styling */
        .main-header {
            background: linear-gradient(90deg, #1f2937, #374151, #4b5563);
            padding: 2.5rem;
            border-radius: 16px;
            margin-bottom: 2rem;
            text-align: center;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.2);
        }
        
        /* Feature cards */
        .feature-card {
            background: #1f2937;
            border: 2px solid #374151;
            border-radius: 12px;
            padding: 18px;
            margin-bottom: 14px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.2);
            transition: all 0.3s ease;
        }
        .feature-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.4), 0 10px 10px -5px rgba(0, 0, 0, 0.3);
        }
        
        /* Model status */
        .model-status {
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 0.9rem;
            margin-bottom: 10px;
            font-weight: 600;
        }
        .status-available {
            background: #064e3b;
            color: #6ee7b7;
            border: 2px solid #10b981;
        }
        .status-unavailable {
            background: #7f1d1d;
            color: #fca5a5;
            border: 2px solid #ef4444;
        }
        .status-partial {
            background: #78350f;
            color: #fcd34d;
            border: 2px solid #f59e0b;
        }
        
        /* Tips container */
        .tips-container {
            background: #064e3b;
            border: 2px solid #10b981;
            border-radius: 12px;
            padding: 18px;
            margin-bottom: 18px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.2);
        }
        .tip-item {
            margin-bottom: 12px;
            padding-left: 28px;
            position: relative;
            color: #6ee7b7;
            font-weight: 500;
            line-height: 1.5;
        }
        .tip-item:before {
            content: "♻️";
            position: absolute;
            left: 0;
        }
        
        /* Input mode selector */
        .input-mode-selector {
            display: flex;
            justify-content: center;
            margin-bottom: 28px;
        }
        
        /* Button styling */
        div.stButton > button:first-child {
            background: linear-gradient(90deg, #3b82f6, #1d4ed8);
            color: white;
            border: none;
            border-radius: 12px;
            padding: 14px 28px;
            font-weight: 600;
            font-size: 1rem;
            box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.4), 0 4px 6px -2px rgba(0, 0, 0, 0.2);
            transition: all 0.3s ease;
        }
        div.stButton > button:first-child:hover {
            background: linear-gradient(90deg, #2563eb, #1e40af);
            box-shadow: 0 20px 25px -5px rgba(59, 130, 246, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.3);
            transform: translateY(-2px);
        }
        
        /* Form styling */
        div[data-testid="stForm"] {
            background: #1f2937;
            border-radius: 16px;
            padding: 28px;
            margin-bottom: 28px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.2);
            border: 2px solid #374151;
        }
        
        /* Text input styling */
        .stTextArea > div > div > textarea {
            background-color: #111827;
            border: 2px solid #4b5563;
            border-radius: 12px;
            color: #f9fafb;
            padding: 16px;
            font-size: 1rem;
            transition: all 0.3s ease;
            font-weight: 500;
        }
        .stTextArea > div > div > textarea:focus {
            border-color: #3b82f6;
            box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.3);
        }
        
        /* Radio button styling */
        div[data-testid="stRadio"] > div > div {
            background: #1f2937;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
            border: 2px solid #374151;
            font-weight: 600;
        }
        
        /* File uploader styling */
        .stFileUploader {
            background: #1f2937;
            border-radius: 12px;
            padding: 24px;
            border: 3px dashed #4b5563;
            transition: all 0.3s ease;
        }
        .stFileUploader:hover {
            border-color: #3b82f6;
            background: #1e3a8a;
        }
        
        /* Sidebar styling */
        .css-1d391kg {
            background: #0f172a;
            padding-top: 2rem;
            border-right: 2px solid #1e2937;
        }
        
        /* Success message styling */
        .element-container .stSuccess {
            background: #064e3b;
            color: #6ee7b7;
            border-radius: 12px;
            padding: 16px 20px;
            border: 2px solid #10b981;
            font-weight: 600;
        }
        
        /* Warning message styling */
        .element-container .stWarning {
            background: #78350f;
            color: #fcd34d;
            border-radius: 12px;
            padding: 16px 20px;
            border: 2px solid #f59e0b;
            font-weight: 600;
        }
        
        /* Error message styling */
        .element-container .stError {
            background: #7f1d1d;
            color: #fca5a5;
            border-radius: 12px;
            padding: 16px 20px;
            border: 2px solid #ef4444;
            font-weight: 600;
        }
        
        /* Info message styling */
        .element-container .stInfo {
            background: #1e3a8a;
            color: #93c5fd;
            border-radius: 12px;
            padding: 16px 20px;
            border: 2px solid #3b82f6;
            font-weight: 600;
        }
        
        /* Section headers */
        h1, h2, h3, h4, h5, h6 {
            color: #f9fafb;
            font-weight: 700;
        }
        
        /* Text color for labels and descriptions */
        label, .stMarkdown, .stText {
            color: #d1d5db;
            font-weight: 500;
        }
        
        /* Dark text on light backgrounds */
        .stTextInput, .stSelectbox, .stSlider {
            color: #f9fafb;
            font-weight: 600;
        }
        
        /* Camera input styling */
        .stCameraInput > label {
            background: #1f2937;
            border: 2px solid #4b5563;
            border-radius: 12px;
            padding: 20px;
            display: block;
            transition: all 0.3s ease;
        }
        .stCameraInput > label:hover {
            border-color: #3b82f6;
            background: #1e3a8a;
        }
        
        /* Image upload styling */
        .stFileUploader > label {
            background: #1f2937;
            border: 2px solid #4b5563;
            border-radius: 12px;
            padding: 20px;
            display: block;
            transition: all 0.3s ease;
        }
        .stFileUploader > label:hover {
            border-color: #3b82f6;
            background: #1e3a8a;
        }
        
        /* Divider styling */
        .stDivider {
            border-color: #374151;
            margin: 2rem 0;
        }
        
        /* Selectbox styling */
        .stSelectbox > div > div > select {
            background-color: #111827;
            border: 2px solid #4b5563;
            border-radius: 8px;
            color: #f9fafb;
            padding: 10px;
            font-weight: 600;
        }
        
        /* Text input styling */
        .stTextInput > div > div > input {
            background-color: #111827;
            border: 2px solid #4b5563;
            border-radius: 8px;
            color: #f9fafb;
            padding: 10px;
            font-weight: 600;
        }
        
        /* Checkbox styling */
        .stCheckbox > label {
            color: #d1d5db;
            font-weight: 600;
        }
        
        /* Spinner styling */
        .stSpinner > div {
            border-top-color: #3b82f6 !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [{
            "role": "assistant",
            "text": "🌿 Hello! I'm WasteBot, your local waste sorting assistant. I'm here to help you dispose of waste responsibly. You can describe an item or upload an image to get detailed disposal guidance. What would you like to classify today?",
            "time": time.time()
        }]
    
    if "input_mode" not in st.session_state:
        st.session_state.input_mode = "Text"
    
    if "logs" not in st.session_state:
        st.session_state.logs = []
    
    # Main header
    st.markdown("""
    <div class="main-header">
        <h1 style="margin: 0; font-size: 3rem; color: white; text-shadow: 0 2px 4px rgba(0,0,0,0.5); font-weight: 800;">♻️ Enhanced Waste Sorter</h1>
        <p style="margin: 10px 0 0 0; opacity: 0.95; color: white; font-size: 1.3rem; font-weight: 600;">Local AI-powered waste classification for responsible disposal</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("Configuration")
        
        # Model selection
        st.subheader("AI Models")
        try:
            # Get available models
            result = subprocess.run(
                ["ollama", "ls"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                models = [line.split()[0] for line in result.stdout.split('\n')[1:] if line.strip()]
            else:
                models = []
        except Exception:
            models = []
        
        if models:
            text_model = st.selectbox(
                "Text Model",
                models,
                index=models.index(DEFAULT_TEXT_MODEL) if DEFAULT_TEXT_MODEL in models else 0
            )
            image_model = st.selectbox(
                "Image Model",
                models,
                index=models.index(DEFAULT_IMAGE_MODEL) if DEFAULT_IMAGE_MODEL in models else 0
            )
        else:
            st.warning("No Ollama models found. Install with: ollama pull llama3")
            text_model = st.text_input("Text Model", DEFAULT_TEXT_MODEL)
            image_model = st.text_input("Image Model", DEFAULT_IMAGE_MODEL)
        
        # Model status
        st.subheader("System Status")
        if models:
            st.markdown('<div class="model-status status-available">✓ Ollama Available</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="model-status status-unavailable">✗ Ollama Not Found</div>', unsafe_allow_html=True)
        
        if OCR_AVAILABLE:
            st.markdown('<div class="model-status status-available">✓ OCR Available</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="model-status status-partial">⚠ OCR Not Installed</div>', unsafe_allow_html=True)
        
        # Settings
        st.subheader("Settings")
        enable_cache = st.checkbox("Enable Caching", value=True)
        debug_mode = st.checkbox("Debug Mode", value=False)
        
        # Actions
        st.subheader("Actions")
        if st.button("Clear Chat History"):
            st.session_state.chat_history = [{
                "role": "assistant",
                "text": "Chat history cleared. How can I help you with waste disposal today?",
                "time": time.time()
            }]
            st.rerun()
        
        if st.button("Export Chat"):
            chat_data = json.dumps(st.session_state.chat_history, indent=2)
            st.download_button(
                "Download Chat History",
                chat_data,
                "wastebot_chat.json",
                "application/json"
            )
        
        # Disposable Tips Section
        st.subheader("Disposable Tips")
        st.markdown("""
        <div class="tips-container">
            <p style="margin-top: 0; color: #6ee7b7; font-weight: 700; font-size: 1.1rem;"><strong>Follow these tips for responsible waste disposal:</strong></p>
            <div class="tip-item">Always rinse containers before recycling to avoid contamination</div>
            <div class="tip-item">Remove caps and lids from bottles as they may be different materials</div>
            <div class="tip-item">Flatten cardboard boxes to save space in recycling bins</div>
            <div class="tip-item">Never put batteries in regular trash - they're hazardous waste</div>
            <div class="tip-item">Compost food scraps to reduce landfill waste</div>
            <div class="tip-item">Use reusable bags instead of plastic bags</div>
            <div class="tip-item">Donate usable items instead of throwing them away</div>
            <div class="tip-item">Check local recycling guidelines as they vary by location</div>
            <div class="tip-item">Avoid single-use items when possible</div>
            <div class="tip-item">Properly dispose of electronic waste at collection points</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Debug info
        if debug_mode:
            st.subheader("Debug Logs")
            st.text_area("Logs", value="\n".join(st.session_state.logs), height=200)
    
    # Main content area
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Chat history
        render_chat_history()
        
        # Input form
        st.divider()
        
        # Input mode selection with improved UI
        st.markdown('<div class="input-mode-selector">', unsafe_allow_html=True)
        input_mode = st.radio(
            "Select Input Type",
            ["Text", "Image"],
            index=["Text", "Image"].index(st.session_state.input_mode),
            horizontal=True,
            key="input_mode_selector"
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Update session state
        st.session_state.input_mode = input_mode
        
        # Handle different input modes
        if input_mode == "Text":
            with st.form("input_form", clear_on_submit=True):
                user_input = st.text_area(
                    "Describe the waste item",
                    height=120,
                    placeholder="e.g., 'banana peels', 'AA battery', 'used syringe'",
                    help="Provide a detailed description of the waste item for better classification"
                )
                submitted = st.form_submit_button("Classify Waste")
                
                if submitted:
                    if not user_input:
                        st.warning("Please provide input before submitting.")
                    else:
                        # Add user message to chat
                        st.session_state.chat_history.append({
                            "role": "user",
                            "text": user_input,
                            "time": time.time()
                        })
                        
                        # Check if user is asking for more information about a category
                        user_input_lower = user_input.lower()
                        category_found = None
                        
                        # Check for category information requests
                        for cat_id, cat_info in CATEGORIES.items():
                            if cat_info["name"].lower() in user_input_lower and ("tell me more" in user_input_lower or "more about" in user_input_lower or "information about" in user_input_lower):
                                category_found = cat_id
                                break
                        
                        if category_found is not None:
                            # Provide detailed information about the requested category
                            details = get_category_details(category_found)
                            category_name = details["category_name"]
                            
                            # Add response to chat
                            response_text = f"Here's detailed information about {category_name}:"
                            st.session_state.chat_history.append({
                                "role": "assistant",
                                "text": response_text,
                                "time": time.time()
                            })
                            
                            # Add disposal info marker to chat
                            st.session_state.chat_history.append({
                                "role": "assistant",
                                "text": f"DISPOSAL_INFO:{category_found}",
                                "time": time.time()
                            })
                            
                            # Follow-up question
                            follow_up = f"Is there anything specific about {category_name.lower()} you'd like to know? Or do you have another item to classify?"
                            st.session_state.chat_history.append({
                                "role": "assistant",
                                "text": follow_up,
                                "time": time.time()
                            })
                            
                        else:
                            # Process classification
                            with st.spinner("Classifying waste..."):
                                try:
                                    category_id, category_name, description, confidence, details = classify_text(
                                        user_input, text_model
                                    )
                                    
                                    # Add result to chat
                                    result_text = f"I've classified this as **{category_name}** with {confidence:.0%} confidence."
                                    st.session_state.chat_history.append({
                                        "role": "assistant",
                                        "text": result_text,
                                        "time": time.time()
                                    })
                                    
                                    # Add disposal info marker to chat
                                    st.session_state.chat_history.append({
                                        "role": "assistant",
                                        "text": f"DISPOSAL_INFO:{category_id}",
                                        "time": time.time()
                                    })
                                    
                                    # Follow-up question
                                    follow_up = f"Is there anything else you'd like to know about disposing of {category_name.lower()}? Or do you have another item to classify?"
                                    st.session_state.chat_history.append({
                                        "role": "assistant",
                                        "text": follow_up,
                                        "time": time.time()
                                    })
                                    
                                except Exception as e:
                                    st.error(f"An error occurred: {str(e)}")
                                    _log(f"Classification error: {str(e)}")
                                    if debug_mode:
                                        st.text_area("Error Details", traceback.format_exc(), height=200)
                        
                        st.rerun()
                        
        elif input_mode == "Image":
            with st.form("input_form", clear_on_submit=True):
                st.markdown("#### Capture or Upload Image")
                img_input = st.camera_input("Take a photo", help="Allow camera access when prompted")
                uploaded_img = st.file_uploader(
                    "Or upload an image",
                    type=["jpg", "jpeg", "png"],
                    help="Supported formats: JPG, PNG"
                )
                user_input = img_input if img_input is not None else uploaded_img
                submitted = st.form_submit_button("Classify Waste")
                
                if submitted:
                    if not user_input:
                        st.warning("Please provide an image before submitting.")
                    else:
                        # Add user message to chat
                        st.session_state.chat_history.append({
                            "role": "user",
                            "text": "[Image uploaded]",
                            "time": time.time()
                        })
                        
                        # Process classification
                        with st.spinner("Classifying waste..."):
                            try:
                                image_bytes = user_input.read()
                                category_id, category_name, description, confidence, details = classify_image(
                                    image_bytes, image_model, text_model
                                )
                                
                                # Add result to chat
                                result_text = f"I've classified this as **{category_name}** with {confidence:.0%} confidence."
                                st.session_state.chat_history.append({
                                    "role": "assistant",
                                    "text": result_text,
                                    "time": time.time()
                                })
                                
                                # Add disposal info marker to chat
                                st.session_state.chat_history.append({
                                    "role": "assistant",
                                    "text": f"DISPOSAL_INFO:{category_id}",
                                    "time": time.time()
                                })
                                
                                # Follow-up question
                                follow_up = f"Is there anything else you'd like to know about disposing of {category_name.lower()}? Or do you have another item to classify?"
                                st.session_state.chat_history.append({
                                    "role": "assistant",
                                    "text": follow_up,
                                    "time": time.time()
                                })
                                
                            except Exception as e:
                                st.error(f"An error occurred: {str(e)}")
                                _log(f"Classification error: {str(e)}")
                                if debug_mode:
                                    st.text_area("Error Details", traceback.format_exc(), height=200)
                        
                        st.rerun()
    
    with col2:
        # Information panel
        st.markdown("### How to Use")
        st.markdown("""
        <div class="feature-card">
            <h4>📝 Text Input</h4>
            <p>Describe the waste item in detail for best results.</p>
        </div>
        <div class="feature-card">
            <h4>📷 Image Input</h4>
            <p>Take a photo or upload an image of the waste item.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Quick category info buttons
        st.markdown("### Quick Category Info")
        for cat_id, cat_info in CATEGORIES.items():
            if st.button(f"{cat_info['icon']} {cat_info['name']}", key=f"quick_info_{cat_id}"):
                # Add user message to chat
                st.session_state.chat_history.append({
                    "role": "user",
                    "text": f"Tell me more about {cat_info['name']}",
                    "time": time.time()
                })
                
                # Add response to chat
                response_text = f"Here's detailed information about {cat_info['name']}:"
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "text": response_text,
                    "time": time.time()
                })
                
                # Add disposal info marker to chat
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "text": f"DISPOSAL_INFO:{cat_id}",
                    "time": time.time()
                })
                
                # Follow-up question
                follow_up = f"Is there anything specific about {cat_info['name'].lower()} you'd like to know? Or do you have another item to classify?"
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "text": follow_up,
                    "time": time.time()
                })
                
                st.rerun()
        
        # Tips
        st.markdown("### Tips for Better Results")
        st.markdown("""
        - Be specific in your descriptions
        - Include material information (plastic, metal, etc.)
        - Mention any hazardous components
        - For images, ensure good lighting
        - Click category buttons for quick information
        """)

if __name__ == "__main__":
    main()
