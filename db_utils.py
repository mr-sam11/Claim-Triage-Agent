# db_utils.py
import os
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME", "claims_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "triage_results")

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

def save_claim_to_db(claim_number: str, claim_data: dict):
    """
    Save claim triage output to MongoDB.
    Each record includes timestamp and claim number.
    """
    record = {
        "_id": claim_number,
        **claim_data,
        "Processed_On": datetime.utcnow().isoformat()
    }
    collection.replace_one({"_id": claim_number}, record, upsert=True)
    print(f"✅ Claim {claim_number} stored in MongoDB.")


# # db_utils.py
# import os
# from pymongo import MongoClient
# from dotenv import load_dotenv
# from datetime import datetime

# # ----------------------------
# # Load environment variables
# # ----------------------------
# load_dotenv()

# MONGODB_URI = os.getenv("MONGODB_URI")
# DB_NAME = os.getenv("DB_NAME", "claims_db")
# COLLECTION_NAME = os.getenv("COLLECTION_NAME", "triage_results")

# # ----------------------------
# # MongoDB Client Setup
# # ----------------------------
# client = MongoClient(MONGODB_URI)
# db = client[DB_NAME]
# collection = db[COLLECTION_NAME]


# # ----------------------------
# # Save Claim Function
# # ----------------------------
# def save_claim_to_db(claim_number: str, claim_data: dict):
#     """
#     Save claim triage output to MongoDB.
#     Each record includes timestamp and claim number.
#     """
#     record = {
#         "_id": claim_number,
#         **claim_data,
#         "Processed_On": datetime.utcnow().isoformat()
#     }

#     # Upsert ensures it updates if already exists
#     result = collection.replace_one({"_id": claim_number}, record, upsert=True)

#     if result.matched_count > 0:
#         print(f"📝 Updated existing claim record: {claim_number}")
#     else:
#         print(f"✅ Inserted new claim record: {claim_number}")


# # ----------------------------
# # Retrieve Claim Function
# # ----------------------------
# def get_claim_from_db(claim_number: str):
#     """
#     Retrieve claim data from MongoDB by claim number.
#     """
#     record = collection.find_one({"_id": claim_number})
#     if record:
#         print(f"📦 Claim {claim_number} retrieved successfully!")
#     else:
#         print(f"⚠️ Claim {claim_number} not found in MongoDB.")
#     return record


# # ----------------------------
# # Test Block
# # ----------------------------
# if __name__ == "__main__":
#     # Sample test data (simulating AI output)
#     sample_claim_number = "CLAIMTEST001"
#     sample_data = {
#         "Claim Type": "Auto",
#         "Claim Summary": "Front bumper damage due to minor collision.",
#         "Severity Level": "Low",
#         "Risk Level": "Low",
#         "Priority": "Low",
#         "Red Flags": "None",
#         "Recommendation": "Approve automatically under low-risk category."
#     }

#     print("\n🚀 Testing MongoDB Connection and Save Operation...\n")
#     save_claim_to_db(sample_claim_number, sample_data)

#     print("\n🔍 Retrieving stored record for verification...\n")
#     result = get_claim_from_db(sample_claim_number)
#     print(result)
