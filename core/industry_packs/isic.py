"""
UN International Standard Industrial Classification of All Economic Activities (ISIC) Rev. 4
Authoritative taxonomy registry for data-driven industry categorization (OpenCode Step 1H).
"""

from typing import Any, Dict, Optional, Set

# Comprehensive UN ISIC Rev. 4 Division Registry
# Maps 2-character / 3-character division codes to standard economic classifications
ISIC_REV4_DIVISIONS: Dict[str, Dict[str, str]] = {
    # Section A — Agriculture, forestry and fishing
    "A01": {"section": "A", "name": "Crop and animal production, hunting and related service activities"},
    "A02": {"section": "A", "name": "Forestry and logging"},
    "A03": {"section": "A", "name": "Fishing and aquaculture"},
    # Section B — Mining and quarrying
    "B05": {"section": "B", "name": "Mining of coal and lignite"},
    "B06": {"section": "B", "name": "Extraction of crude petroleum and natural gas"},
    "B07": {"section": "B", "name": "Mining of metal ores"},
    "B08": {"section": "B", "name": "Other mining and quarrying"},
    "B09": {"section": "B", "name": "Mining support service activities"},
    # Section C — Manufacturing
    "C10": {"section": "C", "name": "Manufacture of food products"},
    "C11": {"section": "C", "name": "Manufacture of beverages"},
    "C12": {"section": "C", "name": "Manufacture of tobacco products"},
    "C13": {"section": "C", "name": "Manufacture of textiles"},
    "C14": {"section": "C", "name": "Manufacture of wearing apparel"},
    "C15": {"section": "C", "name": "Manufacture of leather and related products"},
    "C16": {"section": "C", "name": "Manufacture of wood and of products of wood and cork"},
    "C17": {"section": "C", "name": "Manufacture of paper and paper products"},
    "C18": {"section": "C", "name": "Printing and reproduction of recorded media"},
    "C19": {"section": "C", "name": "Manufacture of coke and refined petroleum products"},
    "C20": {"section": "C", "name": "Manufacture of chemicals and chemical products"},
    "C21": {"section": "C", "name": "Manufacture of pharmaceuticals, medicinal chemical and botanical products"},
    "C22": {"section": "C", "name": "Manufacture of rubber and plastics products"},
    "C23": {"section": "C", "name": "Manufacture of other non-metallic mineral products"},
    "C24": {"section": "C", "name": "Manufacture of basic metals"},
    "C25": {"section": "C", "name": "Manufacture of fabricated metal products, except machinery and equipment"},
    "C26": {"section": "C", "name": "Manufacture of computer, electronic and optical products"},
    "C27": {"section": "C", "name": "Manufacture of electrical equipment"},
    "C28": {"section": "C", "name": "Manufacture of machinery and equipment n.e.c."},
    "C29": {"section": "C", "name": "Manufacture of motor vehicles, trailers and semi-trailers"},
    "C30": {"section": "C", "name": "Manufacture of other transport equipment"},
    "C31": {"section": "C", "name": "Manufacture of furniture"},
    "C32": {"section": "C", "name": "Other manufacturing"},
    "C33": {"section": "C", "name": "Repair and installation of machinery and equipment"},
    # Section D — Electricity, gas, steam and air conditioning supply
    "D35": {"section": "D", "name": "Electricity, gas, steam and air conditioning supply"},
    # Section E — Water supply; sewerage, waste management and remediation activities
    "E36": {"section": "E", "name": "Water collection, treatment and supply"},
    "E37": {"section": "E", "name": "Sewerage"},
    "E38": {"section": "E", "name": "Waste collection, treatment and disposal activities; materials recovery"},
    "E39": {"section": "E", "name": "Remediation activities and other waste management services"},
    # Section F — Construction
    "F41": {"section": "F", "name": "Construction of buildings"},
    "F42": {"section": "F", "name": "Civil engineering"},
    "F43": {"section": "F", "name": "Specialised construction activities"},
    # Section G — Wholesale and retail trade; repair of motor vehicles and motorcycles
    "G45": {"section": "G", "name": "Wholesale and retail trade and repair of motor vehicles and motorcycles"},
    "G46": {"section": "G", "name": "Wholesale trade, except of motor vehicles and motorcycles"},
    "G47": {"section": "G", "name": "Retail trade, except of motor vehicles and motorcycles"},
    # Section H — Transportation and storage
    "H49": {"section": "H", "name": "Land transport and transport via pipelines"},
    "H50": {"section": "H", "name": "Water transport"},
    "H51": {"section": "H", "name": "Air transport"},
    "H52": {"section": "H", "name": "Warehousing and support activities for transportation"},
    "H53": {"section": "H", "name": "Postal and courier activities"},
    # Section I — Accommodation and food service activities
    "I55": {"section": "I", "name": "Accommodation"},
    "I56": {"section": "I", "name": "Food and beverage service activities"},
    # Section J — Information and communication
    "J58": {"section": "J", "name": "Publishing activities"},
    "J59": {"section": "J", "name": "Motion picture, video and television programme production, sound recording"},
    "J60": {"section": "J", "name": "Broadcasting activities"},
    "J61": {"section": "J", "name": "Telecommunications"},
    "J62": {"section": "J", "name": "Computer programming, consultancy and related activities"},
    "J63": {"section": "J", "name": "Information service activities"},
    # Section K — Financial and insurance activities
    "K64": {"section": "K", "name": "Financial service activities, except insurance and pension funding"},
    "K65": {"section": "K", "name": "Insurance, reinsurance and pension funding, except compulsory social security"},
    "K66": {"section": "K", "name": "Activities auxiliary to financial service and insurance activities"},
    # Section L — Real estate activities
    "L68": {"section": "L", "name": "Real estate activities"},
    # Section M — Professional, scientific and technical activities
    "M69": {"section": "M", "name": "Legal and accounting activities"},
    "M70": {"section": "M", "name": "Activities of head offices; management consultancy activities"},
    "M71": {"section": "M", "name": "Architectural and engineering activities; technical testing and analysis"},
    "M72": {"section": "M", "name": "Scientific research and development"},
    "M73": {"section": "M", "name": "Advertising and market research"},
    "M74": {"section": "M", "name": "Other professional, scientific and technical activities"},
    "M75": {"section": "M", "name": "Veterinary activities"},
    # Section N — Administrative and support service activities
    "N77": {"section": "N", "name": "Rental and leasing activities"},
    "N78": {"section": "N", "name": "Employment activities"},
    "N79": {"section": "N", "name": "Travel agency, tour operator, reservation service and related activities"},
    "N80": {"section": "N", "name": "Security and investigation activities"},
    "N81": {"section": "N", "name": "Services to buildings and landscape activities"},
    "N82": {"section": "N", "name": "Office administrative, office support and other business support activities"},
    # Section O — Public administration and defence
    "O84": {"section": "O", "name": "Public administration and defence; compulsory social security"},
    # Section P — Education
    "P85": {"section": "P", "name": "Education"},
    # Section Q — Human health and social work activities
    "Q86": {"section": "Q", "name": "Human health activities"},
    "Q87": {"section": "Q", "name": "Residential care activities"},
    "Q88": {"section": "Q", "name": "Social work activities without accommodation"},
    # Section R — Arts, entertainment and recreation
    "R90": {"section": "R", "name": "Creative, arts and entertainment activities"},
    "R91": {"section": "R", "name": "Libraries, archives, museums and other cultural activities"},
    "R92": {"section": "R", "name": "Gambling and betting activities"},
    "R93": {"section": "R", "name": "Sports activities and amusement and recreation activities"},
    # Section S — Other service activities
    "S94": {"section": "S", "name": "Activities of membership organizations"},
    "S95": {"section": "S", "name": "Repair of computers and personal and household goods"},
    "S96": {"section": "S", "name": "Other personal service activities"},
}


def normalize_isic_code(code: str) -> str:
    """Normalizes an ISIC code to standard uppercase format (e.g. 'j62' -> 'J62', '62' -> 'J62')."""
    if not isinstance(code, str):
        return ""
    clean = code.strip().upper()
    if clean in ISIC_REV4_DIVISIONS:
        return clean

    # Numeric fallback (e.g. '62' -> lookup by division number)
    if clean.isdigit():
        padded = clean.zfill(2)
        for k in ISIC_REV4_DIVISIONS:
            if k[1:] == padded:
                return k

    return clean


def validate_isic_code(code: str) -> bool:
    """Returns True if the code is an authoritative UN ISIC Rev. 4 taxonomy code."""
    normalized = normalize_isic_code(code)
    return normalized in ISIC_REV4_DIVISIONS


def get_isic_details(code: str) -> Optional[Dict[str, str]]:
    """Retrieves standard UN ISIC Rev. 4 metadata for a given code."""
    normalized = normalize_isic_code(code)
    details = ISIC_REV4_DIVISIONS.get(normalized)
    if not details:
        return None
    return {
        "code": normalized,
        "section": details["section"],
        "name": details["name"],
    }
