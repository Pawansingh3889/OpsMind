"""Ingest sample factory documents into ChromaDB for the demo."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from modules.doc_search import ingest_text

# Sample factory documents (simulating real SOPs, HACCP plans, etc.)
SAMPLE_DOCS = {
    'HACCP_Plan_2024.pdf': {
        'category': 'HACCP',
        'content': """
HACCP PLAN — Northshore Seafoods Ltd
Hazard Analysis and Critical Control Points

CRITICAL CONTROL POINT 1: RECEIVING RAW MATERIALS
Hazard: Contaminated or temperature-abused raw fish
Critical Limit: Internal temperature of fish must be between -2°C and 5°C on arrival
Monitoring: Check temperature of every delivery using calibrated probe thermometer
Corrective Action: Reject any delivery above 5°C. Record rejection in supplier log.
Verification: Daily calibration of thermometers. Monthly review of rejection records.

CRITICAL CONTROL POINT 2: COLD STORAGE
Hazard: Bacterial growth due to temperature abuse during storage
Critical Limit: Cold rooms must maintain temperature between 0°C and 4°C at all times
Monitoring: Automated temperature logging every 15 minutes. Manual check every 2 hours.
Corrective Action: If temperature exceeds 5°C for more than 30 minutes, assess product safety. If exceeded 8°C, quarantine all product for QC assessment.
Verification: Weekly review of temperature logs. Monthly calibration of sensors.

CRITICAL CONTROL POINT 3: PROCESSING
Hazard: Cross-contamination, allergen contamination, foreign body contamination
Critical Limit: Processing area temperature must not exceed 12°C. Metal detection on all finished products.
Monitoring: Continuous temperature monitoring. Metal detector checks every hour with test pieces.
Corrective Action: Stop production if area exceeds 15°C. Reject and quarantine any product that fails metal detection.

CRITICAL CONTROL POINT 4: DISPATCH
Hazard: Temperature abuse during loading and transport
Critical Limit: Product temperature must be between 0°C and 4°C at dispatch. Vehicle temperature must be below 5°C.
Monitoring: Check product and vehicle temperature before loading. Record on dispatch log.
Corrective Action: Do not load if vehicle is above 5°C. Re-chill product if above 4°C.
"""
    },
    'SOP_Cold_Room_Temperature.pdf': {
        'category': 'SOP',
        'content': """
STANDARD OPERATING PROCEDURE: Cold Room Temperature Monitoring
Document Number: SOP-CR-001
Revision: 4.0
Effective Date: January 2024

PURPOSE: To ensure all cold storage areas maintain temperatures within food safety limits.

SCOPE: All cold rooms, freezers, and chilled dispatch areas at Northshore Seafoods.

PROCEDURE:
1. Temperature checks must be performed and recorded every 2 hours during operating hours.
2. Use the calibrated digital thermometer (stored in the QC office).
3. Record the temperature on the daily temperature log sheet (Form TC-001).
4. Acceptable temperature ranges:
   - Cold Room 1 (Fresh Fish): 0°C to 4°C
   - Cold Room 2 (Ready to eat): 0°C to 4°C
   - Freezer 1: -18°C or below
   - Dispatch Bay: 0°C to 5°C
   - Production Floor: Below 12°C

5. If temperature is outside acceptable range:
   a. Immediately inform the Shift Manager or Production Manager
   b. Check the refrigeration unit for obvious faults
   c. Do NOT open the door unnecessarily
   d. Contact maintenance if the issue persists for more than 15 minutes
   e. If product safety is compromised, quarantine all affected stock
   f. Complete a Non-Conformance Report (Form NC-001)

RESPONSIBILITY: All staff performing temperature checks must be trained and competent.
"""
    },
    'SOP_Allergen_Management.pdf': {
        'category': 'SOP',
        'content': """
STANDARD OPERATING PROCEDURE: Allergen Management
Document Number: SOP-AL-001

PURPOSE: To prevent allergen cross-contamination and ensure accurate labelling.

ALLERGENS PRESENT ON SITE:
- Fish (all species)
- Crustaceans (prawns, crab)
- Molluscs (mussels, squid)
- Wheat (in breaded products)
- Egg (in batter)
- Milk (in fish pie mix, sauces)
- Celery (in some marinades)
- Mustard (in some coatings)
- Sulphites (in some preserved products)

ALLERGEN MANAGEMENT PROCEDURES:

1. SEGREGATION: Products containing different allergens must be physically separated during storage, preparation, and processing.

2. SCHEDULING: Production must be scheduled to run non-allergen products BEFORE allergen-containing products. If this is not possible, a full validated clean must be performed between runs.

3. CLEANING: Between allergen changeovers:
   - Full strip-down and clean of all contact surfaces
   - Use hot water (above 82°C) and approved detergent
   - Visually inspect all surfaces
   - ATP swab test on 3 random surfaces (must read below 10 RLU)
   - Record results on Allergen Clean Record (Form AL-002)

4. LABELLING: All finished products must display allergen information in bold text in the ingredients list. Any precautionary allergen statements (may contain) must be risk-assessed and approved by the Technical Manager.

5. STAFF: All staff must wash hands and change gloves between handling different allergen products. Staff must not bring food containing allergens into production areas.
"""
    },
    'Lidl_Product_Spec_Salmon.pdf': {
        'category': 'Customer Spec',
        'content': """
LIDL UK — PRODUCT SPECIFICATION
Product: Atlantic Salmon Fillet (skinless, boneless)
Supplier: Northshore Seafoods Ltd
Spec Number: LDL-SAL-2024-001

PRODUCT DESCRIPTION:
Fresh Atlantic Salmon fillets, skinless and boneless, individually vacuum packed.

WEIGHT SPECIFICATION:
- Target weight: 140g per portion (+/- 5g)
- Minimum weight: 135g
- Maximum weight: 150g

QUALITY REQUIREMENTS:
- Colour: Orange-pink, consistent across fillet
- Texture: Firm, elastic flesh. No gaping.
- Odour: Fresh sea smell. No off-odours.
- Foreign bodies: Zero tolerance
- Bones: Pin-bone free (100% check required)
- Blood spots: No more than 2 per fillet, each less than 3mm
- Melanin marks: Acceptable if less than 5mm and on flesh side only

SHELF LIFE:
- Minimum 7 days shelf life on delivery to Lidl RDC
- Total shelf life: 10 days from production
- Storage temperature: 0°C to 2°C

LABELLING REQUIREMENTS:
- Allergens: FISH (in bold)
- Country of origin: Must state origin of fish
- Catch method: Must state (e.g., Farmed, Atlantic Ocean)
- Best before date format: DD/MM/YYYY

DELIVERY:
- Temperature on arrival: 0°C to 2°C (max 4°C)
- Packaging must be intact and clean
- Delivery to Lidl RDC by 06:00 on scheduled days
"""
    },
    'Staff_Handbook_2024.pdf': {
        'category': 'HR',
        'content': """
NORTHSHORE SEAFOODS — STAFF HANDBOOK 2024

WORKING HOURS:
- Standard shifts: Days (06:00-14:00), Afternoons (14:00-22:00), Nights (22:00-06:00)
- Maximum 48 hours per week (averaged over 17 weeks) under Working Time Regulations
- Opt-out available but must be voluntary and in writing
- Minimum 11 hours rest between shifts
- 20-minute break for shifts over 6 hours

HEALTH AND SAFETY:
- All staff must wear provided PPE: hairnet, beard snood (if applicable), white coat, blue gloves, safety boots, ear protection (in noisy areas)
- Report all accidents and near-misses to your Shift Manager immediately
- Complete accident book entry for all incidents
- First aiders: James Wilson (Days), Radu Popescu (Nights)

ABSENCE AND SICK PAY:
- Notify your Shift Manager before your shift start time if unable to attend
- Self-certification for first 7 days
- Doctor's fit note (sick note) required after 7 days
- Statutory Sick Pay (SSP): 116.75 per week for up to 28 weeks

HYGIENE RULES:
- Wash hands: on entry to production, after toilet, after breaks, after handling waste, between tasks
- No jewellery (except plain wedding band)
- No mobile phones in production areas
- No eating, drinking, or chewing gum in production areas
- Cuts must be covered with blue waterproof plasters (available from First Aid box)

DISCIPLINARY:
- Verbal warning → Written warning → Final written warning → Dismissal
- Gross misconduct (theft, violence, falsifying records, drug/alcohol use) = immediate dismissal
"""
    },
}


def seed_documents():
    total_chunks = 0
    for filename, doc in SAMPLE_DOCS.items():
        chunks = ingest_text(filename, doc['content'], doc['category'])
        total_chunks += chunks
        print(f'  + {filename}: {chunks} chunks')
    print(f'\nTotal: {total_chunks} document chunks indexed')


if __name__ == '__main__':
    seed_documents()
