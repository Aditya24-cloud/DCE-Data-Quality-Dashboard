import pandas as pd
import re
from sqlalchemy import create_engine

EXCEL_FILE = "DIC 2026.xlsx"

DB_CONFIG = {
    "host":     "aws-1-ap-northeast-1.pooler.supabase.com",
    "port":     5432,
    "database": "postgres",
    "user":     "postgres.qrftlbjubdinkolkwavi",
    "password": "Adityasingh2026",
}

def check_email(val):
    if pd.isna(val) or str(val).strip() == "":
        return "missing"
    return "valid" if re.match(r'^[\w\.-]+@[\w\.-]+\.\w{2,}$', str(val).strip()) else "invalid"

def check_phone(val):
    if pd.isna(val) or str(val).strip() == "":
        return "missing"
    digits = re.sub(r'\D', '', str(val))
    return "valid" if 7 <= len(digits) <= 15 else "invalid"

def check_website(val):
    if pd.isna(val) or str(val).strip() == "":
        return "missing"
    return "valid" if re.match(r'(https?://)?(www\.)?[\w\-]+\.\w{2,}', str(val).strip(), re.I) else "invalid"

def check_filled(val):
    return "missing" if pd.isna(val) or str(val).strip() == "" else "valid"

def get_engine():
    cfg = DB_CONFIG
    url = f"postgresql+psycopg2://{cfg['user']}:{cfg['password']}@{cfg['host']}:{cfg['port']}/{cfg['database']}"
    return create_engine(url, pool_pre_ping=True, pool_recycle=300)

print("📂 Loading Excel...")
df = pd.read_excel(EXCEL_FILE, dtype=str)
df.columns = df.columns.str.strip()
df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
df.replace(["n/a","na","nil","none","not available","-",".","0000","123"], pd.NA, inplace=True)

df["phone_mobile1_status"]   = df["Mobile1"].apply(check_phone)
df["phone_mobile2_status"]   = df["Mobile2"].apply(check_phone)
df["phone_tele1_status"]     = df["Tele1"].apply(check_phone)
df["phone_tele2_status"]     = df["Tele2"].apply(check_phone)
df["email1_status"]          = df["Email1"].apply(check_email)
df["email2_status"]          = df["Email2"].apply(check_email)
df["website1_status"]        = df["Website1"].apply(check_website)
df["website2_status"]        = df["Website2"].apply(check_website)
df["company_status"]         = df["CompanyName"].apply(check_filled)
df["firstname_status"]       = df["FirstName"].apply(check_filled)
df["lastname_status"]        = df["LastName"].apply(check_filled)
df["designation_status"]     = df["Designation"].apply(check_filled)
df["city_status"]            = df["City"].apply(check_filled)
df["state_status"]           = df["State"].apply(check_filled)
df["country_status"]         = df["Country"].apply(check_filled)
df["pincode_status"]         = df["Pincode"].apply(check_filled)
df["address_status"]         = df["Address"].apply(check_filled)
df["sector_status"]          = df["Sector"].apply(check_filled)
df["subsector_status"]       = df["Sub Sector"].apply(check_filled)
df["category_status"]        = df["Product Category"].apply(check_filled)
df["businesstype_status"]    = df["Business TYpe"].apply(check_filled)
df["source_status"]          = df["Source"].apply(check_filled)
df["status_status"]          = df["Status"].apply(check_filled)
df["event_status"]           = df["Event"].apply(check_filled)

key_fields = ["company_status", "email1_status", "phone_mobile1_status"]
df["row_quality"] = df[key_fields].apply(
    lambda row: "clean"   if all(v == "valid" for v in row)
    else ("partial" if any(v == "valid" for v in row)
    else "poor"), axis=1
)

print(f"✅ Total records : {len(df):,}")
print(f"   Clean rows   : {(df['row_quality']=='clean').sum():,}")
print(f"   Partial rows : {(df['row_quality']=='partial').sum():,}")
print(f"   Poor rows    : {(df['row_quality']=='poor').sum():,}")

print("\n📡 Supabase mein load ho raha hai...")

print("⏳ Loading exhibitors_raw (79k rows — 3-5 min lagega)...")
eng1 = get_engine()
df.to_sql("exhibitors_raw", eng1, if_exists="replace", index=True, index_label="id", chunksize=500)
eng1.dispose()
print(f"✅ exhibitors_raw → {len(df):,} rows")

print("⏳ Loading exhibitors_clean...")
eng2 = get_engine()
clean_df = df[df["row_quality"]=="clean"].copy()
clean_df.to_sql("exhibitors_clean", eng2, if_exists="replace", index=True, index_label="id", chunksize=500)
eng2.dispose()
print(f"✅ exhibitors_clean → {len(clean_df):,} rows")

print("⏳ Loading exhibitors_issues...")
eng3 = get_engine()
issues_df = df[df["row_quality"]!="clean"].copy()
issues_df.to_sql("exhibitors_issues", eng3, if_exists="replace", index=True, index_label="id", chunksize=500)
eng3.dispose()
print(f"✅ exhibitors_issues → {len(issues_df):,} rows")

print(f"\n🎉 Done! 3 tables Supabase mein load ho gayi!")
print(f"   exhibitors_raw    → {len(df):,} rows")
print(f"   exhibitors_clean  → {len(clean_df):,} rows")
print(f"   exhibitors_issues → {len(issues_df):,} rows")