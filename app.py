from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
from sqlalchemy import create_engine, text
import re
import json
import os
import io
from datetime import datetime
from dotenv import load_dotenv
from functools import wraps
import hashlib
import math
import numpy as np

def isFinite(val):
    try:
        return math.isfinite(val)
    except:
        return False

def get_region_by_province(province):
    p = str(province).strip()
    north = ["เชียงใหม่", "เชียงราย", "ลำพูน", "ลำปาง", "แพร่", "น่าน", "พะเยา", "แม่ฮ่องสอน", "อุตรดิตถ์"]
    northeast = ["นครราชสีมา", "ขอนแก่น", "ชัยภูมิ", "เลย", "หนองบัวลำภู", "อุดรธานี", "หนองคาย", "บึงกาฬ", "สกลนคร", "นครพนม", "มุกดาหาร", "กาฬสินธุ์", "มหาสารคาม", "ร้อยเอ็ด", "ยโสธร", "อำนาจเจริญ", "อุบลราชธานี", "ศรีสะเกษ", "สุรินทร์", "บุรีรัมย์"]
    central = ["กรุงเทพมหานคร", "กรุงเทพฯ", "นนทบุรี", "ปทุมธานี", "สมุทรปราการ", "สมุทรสาคร", "สมุทรสงคราม", "นครปฐม", "พระนครศรีอยุธยา", "อ่างทอง", "ลพบุรี", "สิงห์บุรี", "ชัยนาท", "สระบุรี", "นครสวรรค์", "อุทัยธานี", "กำแพงเพชร", "ตาก", "สุโขทัย", "พิษณุโลก", "พิจิตร", "เพชรบูรณ์"]
    east = ["ชลบุรี", "ระยอง", "จันทบุรี", "ตราด", "ฉะเชิงเทรา", "ปราจีนบุรี", "นครนายก", "สระแก้ว"]
    west = ["ราชบุรี", "กาญจนบุรี", "สุพรรณบุรี", "นครปฐม", "เพชรบุรี", "ประจวบคีรีขันธ์"]
    south = ["นครศรีธรรมราช", "กระบี่", "พังงา", "ภูเก็ต", "สุราษฎร์ธานี", "ระนอง", "ชุมพร", "สงขลา", "สตูล", "ตรัง", "พัทลุง", "ปัตตานี", "ยะลา", "นราธิวาส"]
    if p in north: return "ภาคเหนือ"
    if p in northeast: return "ภาคตะวันออกเฉียงเหนือ"
    if p in central: return "ภาคกลาง"
    if p in east: return "ภาคตะวันออก"
    if p in west: return "ภาคตะวันตก"
    if p in south: return "ภาคใต้"
    return "ไม่ระบุ"

load_dotenv()
app = Flask(__name__)

# ==========================================
# 🛡️ ระบบรักษาความปลอดภัย API
# ==========================================
def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token or ":" not in token:
            return jsonify({'success': False, 'message': 'Access Denied: ปฏิเสธการเข้าถึง กรุณาเข้าสู่ระบบแอดมินก่อน'}), 401
        try:
            username, p_hash = token.split(':', 1)
            with engine.connect() as conn:
                user = conn.execute(text("SELECT password_hash, status FROM `admin_users` WHERE username = :u"), {"u": username}).fetchone()
                if not user or user[0] != p_hash:
                    return jsonify({'success': False, 'message': 'Access Denied: บัญชีหรือรหัสผ่านแอดมินไม่ถูกต้อง'}), 401
                if user[1] in ('pending', 'rejected'):
                    return jsonify({'success': False, 'message': 'Access Denied: บัญชีของคุณยังไม่ได้รับอนุมัติหรือถูกระงับการใช้งาน'}), 403
        except Exception as e:
            return jsonify({'success': False, 'message': f'Access Denied: เกิดข้อผิดพลาดในการตรวจสอบสิทธิ์ ({str(e)})'}), 401
        return f(*args, **kwargs)
    return decorated_function

def get_admin_username():
    token = request.headers.get('Authorization')
    if token and ":" in token:
        return token.split(':', 1)[0]
    return "unknown"

def log_audit(username, action, target, details=None):
    try:
        ip = request.remote_addr
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO `audit_logs` (`username`, `action`, `target`, `details`, `ip_address`) VALUES (:u, :a, :t, :d, :ip)"), {"u": username, "a": action, "t": target, "d": details, "ip": ip})
    except Exception as e:
        print(f"❌ ROPA Log Error: {e}")

def log_visit(page_name, action_type):
    try:
        ip = request.remote_addr
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO `user_visits` (`page_name`, `action_type`, `ip_address`) VALUES (:p, :a, :ip)"), {"p": page_name, "a": action_type, "ip": ip})
    except Exception as e:
        print(f"❌ Visit Log Error: {e}")

API_TO_DB_REF_MAP = {
    'hospcode': 'รหัสหน่วยบริการ', 'check_date': 'วันที่ตรวจ', 'region': 'ภาค', 'health_zone': 'เขตสุขภาพ',
    'province': 'จังหวัด', 'district': 'อำเภอ', 'subdistrict': 'ตำบล', 'location_name': 'สถานที่',
    'water_type': 'ประเภทแหล่งน้ำ', 'water_category': 'กลุ่มแหล่งน้ำ', 'fluoride_level': 'ปริมาณฟลูออไรด์ (mg/L)', 'status': 'สถานการณ์',
    'latitude': 'ละติจูด', 'longitude': 'ลองจิจูด', 'total_kids': 'จำนวนเด็กทั้งหมด',
    'screened_kids': 'จำนวนตรวจ', 'fluorosis_cases': 'พบฟันตกกระ', 'pct_fluorosis': 'ร้อยละเด็กฟันตกกระ',
    'severe_cases': 'severe_cases', 'hosp_name': 'ชื่อหน่วยบริการ', 'dean_index_status': 'สถานการณ์',
    'house_no': 'บ้านเลขที่', 'moo': 'หมู่ที่', 'remark': 'หมายเหตุ', 'data_source': 'แหล่งข้อมูล'
}

def validate_row_data(row_dict, cat):
    errors = []
    
    if cat == 'health':
        num_cols = {
            'total_kids': 'จำนวนเด็กทั้งหมด',
            'screened_kids': 'จำนวนตรวจ',
            'fluorosis_cases': 'พบฟันตกกระ',
            'pct_fluorosis': 'ร้อยละเด็กฟันตกกระ',
            'severe_cases': 'severe_cases',
            'latitude': 'ละติจูด',
            'longitude': 'ลองจิจูด'
        }
    else:
        num_cols = {
            'fluoride_level': 'ปริมาณฟลูออไรด์',
            'latitude': 'ละติจูด',
            'longitude': 'ลองจิจูด'
        }
        
    for col, th_name in num_cols.items():
        val = row_dict.get(col)
        if val is not None and str(val).strip() != '':
            try:
                float_val = float(val)
                row_dict[col] = float_val
            except ValueError:
                errors.append(f"คอลัมน์ [{th_name}] ต้องเป็นตัวเลข แต่พบค่า: '{val}'")
                
    if cat == 'health':
        sk = row_dict.get('screened_kids', 0)
        fc = row_dict.get('fluorosis_cases', 0)
        tk = row_dict.get('total_kids', 0)
        if isinstance(sk, (int, float)) and isinstance(fc, (int, float)):
            if fc > sk:
                errors.append(f"พบฟันตกกระ ({fc}) มากกว่าจำนวนที่ตรวจ ({sk})")
        if isinstance(tk, (int, float)) and isinstance(sk, (int, float)):
            if sk > tk:
                errors.append(f"จำนวนตรวจ ({sk}) มากกว่าจำนวนเด็กทั้งหมด ({tk})")
                
    return errors

# ==========================================
# 1. การเชื่อมต่อฐานข้อมูล
# ==========================================
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '') 
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = os.environ.get('DB_PORT', '3306')     
DB_NAME = os.environ.get('DB_NAME', 'moph_fluoride_db')

DB_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DB_URI)

def init_database_tables():
    print("⚙️ กำลังตรวจสอบตารางและตั้งค่าระบบ (อัปเกรด Blueprint ล่าสุด)...")
    try:
        with engine.begin() as conn:
            # Create admin_users table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS `admin_users` (
                  `id` INT AUTO_INCREMENT PRIMARY KEY,
                  `username` VARCHAR(50) NOT NULL UNIQUE,
                  `password_hash` VARCHAR(255) NOT NULL,
                  `role` VARCHAR(50) DEFAULT 'admin',
                  `fullname` VARCHAR(150),
                  `status` VARCHAR(20) DEFAULT 'approved',
                  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """))
            try:
                conn.execute(text("ALTER TABLE `admin_users` ADD COLUMN `fullname` VARCHAR(150);"))
                conn.execute(text("ALTER TABLE `admin_users` ADD COLUMN `status` VARCHAR(20) DEFAULT 'approved';"))
            except:
                pass
            
            # Create child_fluorosis_cases table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS `child_fluorosis_cases` (
                  `id` INT AUTO_INCREMENT PRIMARY KEY,
                  `fullname` VARCHAR(150) NOT NULL,
                  `gender` VARCHAR(10),
                  `age` INT,
                  `grade` VARCHAR(50),
                  `school` VARCHAR(150),
                  `province` VARCHAR(100),
                  `district` VARCHAR(100),
                  `subdistrict` VARCHAR(100),
                  `address` TEXT,
                  `years_in_area` INT,
                  `survey_date` DATE,
                  `water_source` VARCHAR(100),
                  `water_source_other` VARCHAR(100),
                  `tooth_u1` VARCHAR(5), `tooth_u2` VARCHAR(5), `tooth_u3` VARCHAR(5), `tooth_u4` VARCHAR(5), `tooth_u5` VARCHAR(5), `tooth_u6` VARCHAR(5), `tooth_u7` VARCHAR(5),
                  `tooth_l1` VARCHAR(5), `tooth_l2` VARCHAR(5), `tooth_l3` VARCHAR(5), `tooth_l4` VARCHAR(5), `tooth_l5` VARCHAR(5), `tooth_l6` VARCHAR(5), `tooth_l7` VARCHAR(5),
                  `deans_index` VARCHAR(10),
                  `created_by` VARCHAR(50),
                  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """))

            # Seed default admin user if not exists
            admin_exists = conn.execute(text("SELECT COUNT(*) FROM `admin_users` WHERE `username` = 'admin'")).fetchone()[0]
            if admin_exists == 0:
                conn.execute(text("INSERT INTO `admin_users` (`username`, `password_hash`, `role`) VALUES ('admin', :ph, 'admin')"), {"ph": hashlib.sha256('admin'.encode()).hexdigest()})

            # Create audit_logs table (ROPA)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS `audit_logs` (
                  `id` INT AUTO_INCREMENT PRIMARY KEY,
                  `username` VARCHAR(50) NOT NULL,
                  `action` VARCHAR(100) NOT NULL,
                  `target` VARCHAR(100) NOT NULL,
                  `details` TEXT DEFAULT NULL,
                  `ip_address` VARCHAR(50) DEFAULT NULL,
                  `timestamp` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """))

            # Create user_visits table (Stats)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS `user_visits` (
                  `id` INT AUTO_INCREMENT PRIMARY KEY,
                  `page_name` VARCHAR(100) NOT NULL,
                  `action_type` VARCHAR(50) NOT NULL,
                  `ip_address` VARCHAR(50) DEFAULT NULL,
                  `visited_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS `report_schemas` (
                  `id` INT(11) NOT NULL AUTO_INCREMENT,
                  `report_name` VARCHAR(255) NOT NULL,
                  `category` VARCHAR(50) NOT NULL,
                  `schema_data` JSON NOT NULL,
                  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                  PRIMARY KEY (`id`),
                  UNIQUE KEY `unique_report_name` (`report_name`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """))
            
            # Create health_facilities_master table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS `health_facilities_master` (
                  `hospcode` VARCHAR(50) NOT NULL PRIMARY KEY,
                  `hosp_name` VARCHAR(255) NOT NULL,
                  `facility_type` VARCHAR(100) DEFAULT NULL,
                  `affiliation` VARCHAR(100) DEFAULT NULL,
                  `health_zone` VARCHAR(50) DEFAULT NULL,
                  `province` VARCHAR(100) DEFAULT NULL,
                  `district` VARCHAR(100) DEFAULT NULL,
                  `subdistrict` VARCHAR(100) DEFAULT NULL,
                  `moo` VARCHAR(50) DEFAULT NULL,
                  `zipcode` VARCHAR(50) DEFAULT NULL,
                  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """))
            
            # Create water_records table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS `water_records` (
                  `id` INT AUTO_INCREMENT PRIMARY KEY,
                  `water_type` VARCHAR(100) DEFAULT NULL,
                  `water_category` VARCHAR(100) DEFAULT NULL,
                  `location_name` VARCHAR(255) NOT NULL,
                  `fluoride_level` DOUBLE DEFAULT 0.0,
                  `check_date` VARCHAR(50) DEFAULT NULL,
                  `house_no` VARCHAR(50) DEFAULT NULL,
                  `moo` VARCHAR(50) DEFAULT NULL,
                  `subdistrict` VARCHAR(100) DEFAULT NULL,
                  `district` VARCHAR(100) DEFAULT NULL,
                  `province` VARCHAR(100) DEFAULT NULL,
                  `health_zone` VARCHAR(50) DEFAULT NULL,
                  `region` VARCHAR(100) DEFAULT NULL,
                  `latitude` DOUBLE DEFAULT 0.0,
                  `longitude` DOUBLE DEFAULT 0.0,
                  `remark` TEXT DEFAULT NULL,
                  `data_source` VARCHAR(100) DEFAULT NULL,
                  `status` VARCHAR(100) DEFAULT NULL,
                  UNIQUE KEY `unique_water_key` (`check_date`, `location_name`, `house_no`, `moo`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """))

            # Create dental_records table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS `dental_records` (
                  `id` INT AUTO_INCREMENT PRIMARY KEY,
                  `hospcode` VARCHAR(50) NOT NULL,
                  `hosp_name` VARCHAR(255) DEFAULT NULL,
                  `fiscal_year` VARCHAR(50) NOT NULL,
                  `region` VARCHAR(100) DEFAULT NULL,
                  `health_zone` VARCHAR(50) DEFAULT NULL,
                  `province` VARCHAR(100) DEFAULT NULL,
                  `district` VARCHAR(100) DEFAULT NULL,
                  `subdistrict` VARCHAR(100) DEFAULT NULL,
                  `total_kids` INT DEFAULT 0,
                  `screened_kids` INT DEFAULT 0,
                  `fluorosis_cases` INT DEFAULT 0,
                  `pct_fluorosis` DOUBLE DEFAULT 0.0,
                  `severe_cases` INT DEFAULT 0,
                  `dean_index_status` VARCHAR(100) DEFAULT NULL,
                  `status` VARCHAR(100) DEFAULT NULL,
                  `latitude` DOUBLE DEFAULT 0.0,
                  `longitude` DOUBLE DEFAULT 0.0,
                  `remark` TEXT DEFAULT NULL,
                  `data_source` VARCHAR(100) DEFAULT NULL,
                  UNIQUE KEY `unique_dental_key` (`fiscal_year`, `hospcode`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """))

            # Auto-seed water_records if empty
            water_count = conn.execute(text("SELECT COUNT(*) FROM `water_records`")).fetchone()[0]
            if water_count == 0:
                print("Seeding water_records from excel...")
                for path in ['water_mock_data.xlsx', 'water_data.xlsx']:
                    if os.path.exists(path):
                        df = pd.read_excel(path)
                        if 'ลำดับ' in df.columns:
                            df = df.drop(columns=['ลำดับ'])
                        df.rename(columns=COLUMN_MAP_REV, inplace=True)
                        if 'health_zone' not in df.columns: df['health_zone'] = 'ไม่ระบุ'
                        if 'region' not in df.columns: df['region'] = 'ไม่ระบุ'
                        if 'status' not in df.columns: df['status'] = 'ไม่ระบุ'
                        if 'remark' not in df.columns: df['remark'] = '-'
                        if 'data_source' not in df.columns: df['data_source'] = 'ระบบอัตโนมัติ'
                        
                        for _, row in df.iterrows():
                            row_dict = {k: v for k, v in row.dropna().to_dict().items() if k in VALID_DB_COLUMNS}
                            if len(row_dict) > 0:
                                placeholders = ", ".join([f":{k}" for k in row_dict.keys()])
                                cols = ", ".join([f"`{k}`" for k in row_dict.keys()])
                                updates = ", ".join([f"`{k}`=VALUES(`{k}`)" for k in row_dict.keys()])
                                sql = text(f"INSERT INTO `water_records` ({cols}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {updates}")
                                conn.execute(sql, row_dict)
                        print(f"Seeded water records successfully from {path}.")
                        break

            # Auto-seed dental_records if empty
            dental_count = conn.execute(text("SELECT COUNT(*) FROM `dental_records`")).fetchone()[0]
            if dental_count == 0:
                print("Seeding dental_records from excel...")
                if os.path.exists('dental_data.xlsx'):
                    df = pd.read_excel('dental_data.xlsx')
                    df.rename(columns=COLUMN_MAP_REV, inplace=True)
                    if 'health_zone' not in df.columns: df['health_zone'] = 'ไม่ระบุ'
                    if 'region' not in df.columns: df['region'] = 'ไม่ระบุ'
                    if 'status' not in df.columns: df['status'] = 'ไม่ระบุ'
                    if 'remark' not in df.columns: df['remark'] = '-'
                    if 'data_source' not in df.columns: df['data_source'] = 'ระบบอัตโนมัติ'
                    if 'fiscal_year' not in df.columns: df['fiscal_year'] = str(datetime.now().year + 543)
                    
                    for _, row in df.iterrows():
                        row_dict = {k: v for k, v in row.dropna().to_dict().items() if k in VALID_DB_COLUMNS}
                        if len(row_dict) > 0:
                            placeholders = ", ".join([f":{k}" for k in row_dict.keys()])
                            cols = ", ".join([f"`{k}`" for k in row_dict.keys()])
                            updates = ", ".join([f"`{k}`=VALUES(`{k}`)" for k in row_dict.keys()])
                            sql = text(f"INSERT INTO `dental_records` ({cols}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {updates}")
                            conn.execute(sql, row_dict)
                    print("Seeded dental records successfully.")

            # Create fluorosis_investigations table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS `fluorosis_investigations` (
                  `id` INT AUTO_INCREMENT PRIMARY KEY,
                  `hospcode` VARCHAR(50) NOT NULL,
                  `hosp_name` VARCHAR(255) DEFAULT NULL,
                  `investigation_date` VARCHAR(50) NOT NULL,
                  `patient_gender` VARCHAR(20) DEFAULT NULL,
                  `patient_age` INT DEFAULT 0,
                  `severity_level` VARCHAR(100) NOT NULL,
                  `drinking_water_source` VARCHAR(255) DEFAULT NULL,
                  `exposure_years` INT DEFAULT 0,
                  `investigator_name` VARCHAR(255) DEFAULT NULL,
                  `investigator_phone` VARCHAR(100) DEFAULT NULL,
                  `details` TEXT DEFAULT NULL,
                  `status` VARCHAR(50) DEFAULT 'Pending',
                  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """))

            # Auto-seed fluorosis_investigations if empty
            inv_count = conn.execute(text("SELECT COUNT(*) FROM `fluorosis_investigations`")).fetchone()[0]
            if inv_count == 0:
                pass # Removed mock data for production

            # 💡 [อัปเกรด] Schema JSON ของหน้าหลัก เพื่อให้แก้ไขได้ผ่านหน้าตั้งค่า
            conn.execute(text("""
                INSERT INTO `report_schemas` (`report_name`, `category`, `schema_data`) VALUES
                ('หน้าหลัก', 'summary', '{"fields": [], "config": {"proportion": "", "proportion_rules": [], "drilldown": "", "map": "", "kpis": [{"label":"น้ำเกินมาตรฐานสะสม", "type":"avg", "col":"w_pct", "color":"danger"}, {"label":"เด็กพบฟันตกกระสะสม", "type":"avg", "col":"d_pct", "color":"theme"}, {"label":"พื้นที่เฝ้าระวังสูงสุด", "type":"sum", "col":"red_zones", "color":"warning"}, {"label":"พื้นที่ในเกณฑ์ปลอดภัย", "type":"sum", "col":"safe_zones", "color":"success"}]}}')
                ON DUPLICATE KEY UPDATE report_name=report_name
            """))

            conn.execute(text("""
                INSERT INTO `report_schemas` (`report_name`, `category`, `schema_data`) VALUES
                ('สภาวะฟันตกกระ (เด็ก)', 'health', '{"fields": [{"name": "รหัสหน่วยบริการ", "type": "DB_Column", "db_ref": "hospcode", "formula": ""}, {"name": "ชื่อหน่วยบริการ", "type": "DB_Column", "db_ref": "hosp_name", "formula": ""}, {"name": "ปีงบประมาณ", "type": "DB_Column", "db_ref": "fiscal_year", "formula": ""}, {"name": "เขตสุขภาพ", "type": "DB_Column", "db_ref": "health_zone", "formula": ""}, {"name": "จังหวัด", "type": "DB_Column", "db_ref": "province", "formula": ""}, {"name": "จำนวนตรวจ", "type": "DB_Column", "db_ref": "screened_kids", "formula": ""}, {"name": "พบฟันตกกระ", "type": "DB_Column", "db_ref": "fluorosis_cases", "formula": ""}, {"name": "ร้อยละตกกระ (%)", "type": "Formula", "db_ref": "", "formula": "([พบฟันตกกระ]/[จำนวนตรวจ])*100"}], "config": {"proportion": "สถานการณ์", "proportion_rules": [], "drilldown": "ร้อยละตกกระ (%)", "map": "ร้อยละตกกระ (%)", "kpis": [{"label":"จำนวนเด็กทั้งหมด", "type":"sum", "col":"จำนวนเด็กทั้งหมด", "color":"main"}, {"label":"ได้รับการตรวจ", "type":"sum", "col":"จำนวนตรวจ", "color":"theme"}, {"label":"พบฟันตกกระ", "type":"sum", "col":"พบฟันตกกระ", "color":"danger"}, {"label":"ค่าเฉลี่ยตกกระ", "type":"avg", "col":"ร้อยละตกกระ (%)", "color":"warning"}]}}'),
                
                ('แหล่งน้ำดิบ', 'env', '{"fields": [{"name": "ชนิดน้ำ", "type": "DB_Column", "db_ref": "water_type", "formula": ""}, {"name": "สถานที่เก็บ", "type": "DB_Column", "db_ref": "location_name", "formula": ""}, {"name": "ปริมาณฟลูออไรด์", "type": "DB_Column", "db_ref": "fluoride_level", "formula": ""}, {"name": "ว/ด/ป ที่เก็บ", "type": "DB_Column", "db_ref": "check_date", "formula": ""}, {"name": "บ้านเลขที่", "type": "DB_Column", "db_ref": "house_no", "formula": ""}, {"name": "หมู่ที่", "type": "DB_Column", "db_ref": "moo", "formula": ""}, {"name": "ตำบล", "type": "DB_Column", "db_ref": "subdistrict", "formula": ""}, {"name": "อำเภอ", "type": "DB_Column", "db_ref": "district", "formula": ""}, {"name": "จังหวัด", "type": "DB_Column", "db_ref": "province", "formula": ""}, {"name": "เขตสุขภาพ", "type": "DB_Column", "db_ref": "health_zone", "formula": ""}, {"name": "ภาค", "type": "DB_Column", "db_ref": "region", "formula": ""}, {"name": "ละติจูด", "type": "DB_Column", "db_ref": "latitude", "formula": ""}, {"name": "ลองจิจูด", "type": "DB_Column", "db_ref": "longitude", "formula": ""}, {"name": "หมายเหตุ", "type": "DB_Column", "db_ref": "remark", "formula": ""}, {"name": "แหล่งข้อมูล", "type": "DB_Column", "db_ref": "data_source", "formula": ""}, {"name": "สถานการณ์", "type": "DB_Column", "db_ref": "status", "formula": ""}], "config": {"proportion": "สถานการณ์", "proportion_rules": [], "drilldown": "ปริมาณฟลูออไรด์", "map": "ปริมาณฟลูออไรด์", "kpis": [{"label":"จำนวนจุดตรวจ", "type":"count", "col":"", "color":"main"}, {"label":"ค่าเฉลี่ยฟลูออไรด์", "type":"avg", "col":"ปริมาณฟลูออไรด์", "color":"theme"}, {"label":"สัดส่วนเกินเกณฑ์", "type":"count", "col":"", "color":"danger"}, {"label":"จุดที่ปลอดภัย", "type":"count", "col":"", "color":"success"}]}}'),
                
                ('แหล่งน้ำบริโภค', 'env', '{"fields": [{"name": "ชนิดน้ำ", "type": "DB_Column", "db_ref": "water_type", "formula": ""}, {"name": "สถานที่เก็บ", "type": "DB_Column", "db_ref": "location_name", "formula": ""}, {"name": "ปริมาณฟลูออไรด์", "type": "DB_Column", "db_ref": "fluoride_level", "formula": ""}, {"name": "ว/ด/ป ที่เก็บ", "type": "DB_Column", "db_ref": "check_date", "formula": ""}, {"name": "บ้านเลขที่", "type": "DB_Column", "db_ref": "house_no", "formula": ""}, {"name": "หมู่ที่", "type": "DB_Column", "db_ref": "moo", "formula": ""}, {"name": "ตำบล", "type": "DB_Column", "db_ref": "subdistrict", "formula": ""}, {"name": "อำเภอ", "type": "DB_Column", "db_ref": "district", "formula": ""}, {"name": "จังหวัด", "type": "DB_Column", "db_ref": "province", "formula": ""}, {"name": "เขตสุขภาพ", "type": "DB_Column", "db_ref": "health_zone", "formula": ""}, {"name": "ภาค", "type": "DB_Column", "db_ref": "region", "formula": ""}, {"name": "ละติจูด", "type": "DB_Column", "db_ref": "latitude", "formula": ""}, {"name": "ลองจิจูด", "type": "DB_Column", "db_ref": "longitude", "formula": ""}, {"name": "หมายเหตุ", "type": "DB_Column", "db_ref": "remark", "formula": ""}, {"name": "แหล่งข้อมูล", "type": "DB_Column", "db_ref": "data_source", "formula": ""}, {"name": "สถานการณ์", "type": "DB_Column", "db_ref": "status", "formula": ""}], "config": {"proportion": "สถานการณ์", "proportion_rules": [], "drilldown": "ปริมาณฟลูออไรด์", "map": "ปริมาณฟลูออไรด์", "kpis": [{"label":"จำนวนจุดตรวจ", "type":"count", "col":"", "color":"main"}, {"label":"ค่าเฉลี่ยฟลูออไรด์", "type":"avg", "col":"ปริมาณฟลูออไรด์", "color":"theme"}, {"label":"สัดส่วนเกินเกณฑ์", "type":"count", "col":"", "color":"danger"}, {"label":"จุดที่ปลอดภัย", "type":"count", "col":"", "color":"success"}]}}'),
                
                ('แหล่งน้ำประปา', 'env', '{"fields": [{"name": "ชนิดน้ำ", "type": "DB_Column", "db_ref": "water_type", "formula": ""}, {"name": "สถานที่เก็บ", "type": "DB_Column", "db_ref": "location_name", "formula": ""}, {"name": "ปริมาณฟลูออไรด์", "type": "DB_Column", "db_ref": "fluoride_level", "formula": ""}, {"name": "ว/ด/ป ที่เก็บ", "type": "DB_Column", "db_ref": "check_date", "formula": ""}, {"name": "บ้านเลขที่", "type": "DB_Column", "db_ref": "house_no", "formula": ""}, {"name": "หมู่ที่", "type": "DB_Column", "db_ref": "moo", "formula": ""}, {"name": "ตำบล", "type": "DB_Column", "db_ref": "subdistrict", "formula": ""}, {"name": "อำเภอ", "type": "DB_Column", "db_ref": "district", "formula": ""}, {"name": "จังหวัด", "type": "DB_Column", "db_ref": "province", "formula": ""}, {"name": "เขตสุขภาพ", "type": "DB_Column", "db_ref": "health_zone", "formula": ""}, {"name": "ภาค", "type": "DB_Column", "db_ref": "region", "formula": ""}, {"name": "ละติจูด", "type": "DB_Column", "db_ref": "latitude", "formula": ""}, {"name": "ลองจิจูด", "type": "DB_Column", "db_ref": "longitude", "formula": ""}, {"name": "หมายเหตุ", "type": "DB_Column", "db_ref": "remark", "formula": ""}, {"name": "แหล่งข้อมูล", "type": "DB_Column", "db_ref": "data_source", "formula": ""}, {"name": "สถานการณ์", "type": "DB_Column", "db_ref": "status", "formula": ""}], "config": {"proportion": "สถานการณ์", "proportion_rules": [], "drilldown": "ปริมาณฟลูออไรด์", "map": "ปริมาณฟลูออไรด์", "kpis": [{"label":"จำนวนจุดตรวจ", "type":"count", "col":"", "color":"main"}, {"label":"ค่าเฉลี่ยฟลูออไรด์", "type":"avg", "col":"ปริมาณฟลูออไรด์", "color":"theme"}, {"label":"สัดส่วนเกินเกณฑ์", "type":"count", "col":"", "color":"danger"}, {"label":"จุดที่ปลอดภัย", "type":"count", "col":"", "color":"success"}]}}')
                ON DUPLICATE KEY UPDATE report_name=report_name
            """))

            # Create database indexes for optimized search performance
            for idx_sql in [
                "CREATE INDEX `idx_water_geo` ON `water_records` (`region`, `health_zone`, `province`, `district`)",
                "CREATE INDEX `idx_dental_geo` ON `dental_records` (`region`, `health_zone`, `province`, `district`)",
                "CREATE INDEX `idx_water_date` ON `water_records` (`check_date`)",
                "CREATE INDEX `idx_dental_year` ON `dental_records` (`fiscal_year`)"
            ]:
                try: conn.execute(text(idx_sql))
                except Exception: pass
    except Exception as e: print(f"❌ Error: {e}")

def seed_health_facilities_master():
    try:
        with engine.connect() as conn:
            cnt = conn.execute(text("SELECT COUNT(*) FROM `health_facilities_master`")).fetchone()[0]
        if cnt > 0:
            print("ℹ️ ทะเบียนหน่วยบริการกลาง health_facilities_master มีข้อมูลแล้ว ไม่ต้อง Seed เพิ่ม")
            return
            
        path = "health_office.xlsx"
        if not os.path.exists(path):
            print("⚠️ ไม่พบไฟล์ health_office.xlsx ที่ระบบ งดการ Seeding")
            return
            
        print("📥 กำลังนำเข้าทะเบียนหน่วยบริการกลาง 44,181 รายการจาก health_office.xlsx (กรุณารอสักครู่)...")
        df = pd.read_excel(path)
        
        df.rename(columns={
            'ชื่อ': 'hosp_name',
            'รหัส 5 หลัก': 'hospcode',
            'ประเภทหน่วยบริการสุขภาพ': 'facility_type',
            'สังกัด': 'affiliation',
            'เขตบริการ': 'health_zone',
            'จังหวัด': 'province',
            'อำเภอ/เขต': 'district',
            'ตำบล/แขวง': 'subdistrict',
            'หมู่': 'moo',
            'รหัสไปรษณีย์': 'zipcode'
        }, inplace=True)
        
        valid_cols = ['hospcode', 'hosp_name', 'facility_type', 'affiliation', 'health_zone', 'province', 'district', 'subdistrict', 'moo', 'zipcode']
        df = df[[c for c in valid_cols if c in df.columns]]
        
        df = df.dropna(subset=['hospcode'])
        
        def clean_hospcode(val):
            try:
                val_str = str(val).strip()
                if '.' in val_str:
                    val_str = val_str.split('.')[0]
                val_str = val_str.zfill(5)
                return val_str
            except:
                return None
                
        df['hospcode'] = df['hospcode'].apply(clean_hospcode)
        df = df.dropna(subset=['hospcode'])
        df = df[df['hospcode'] != '00000']
        df = df.drop_duplicates(subset=['hospcode'])
        
        df.to_sql('health_facilities_master', con=engine, if_exists='append', index=False, chunksize=1000)
        print(f"✅ นำเข้าทะเบียนหน่วยบริการกลางสำเร็จ! จำนวน {len(df)} แห่ง")
        
        if len(df) == 0:
            print("ℹ️ ทะเบียนหน่วยบริการกลางในไฟล์ health_office.xlsx ไม่มีรหัส 5 หลัก ระบบจะนำเข้ารายการหน่วยบริการอ้างอิงจำลองเพื่อให้นำเข้าข้อมูลตรวจได้")
            mock_locs = [
                {"hospcode": "10970", "hosp_name": "รพ.พระนั่งเกล้า", "province": "นนทบุรี", "district": "เมืองนนทบุรี", "subdistrict": "บางกระสอ", "health_zone": "4"},
                {"hospcode": "10971", "hosp_name": "รพ.บางบัวทอง", "province": "นนทบุรี", "district": "บางบัวทอง", "subdistrict": "โสนลอย", "health_zone": "4"},
                {"hospcode": "11033", "hosp_name": "รพ.ปากเกร็ด", "province": "นนทบุรี", "district": "ปากเกร็ด", "subdistrict": "ปากเกร็ด", "health_zone": "4"},
                {"hospcode": "10665", "hosp_name": "รพ.สต.ไทรม้า", "province": "นนทบุรี", "district": "เมืองนนทบุรี", "subdistrict": "ไทรม้า", "health_zone": "4"},
                {"hospcode": "10666", "hosp_name": "รพ.สต.บางรักใหญ่", "province": "นนทบุรี", "district": "บางบัวทอง", "subdistrict": "บางรักใหญ่", "health_zone": "4"},
                {"hospcode": "10672", "hosp_name": "รพ.สต.บางแม่นาง", "province": "นนทบุรี", "district": "บางใหญ่", "subdistrict": "บางแม่นาง", "health_zone": "4"},
                {"hospcode": "10674", "hosp_name": "รพ.สต.เสาธงหิน", "province": "นนทบุรี", "district": "บางใหญ่", "subdistrict": "เสาธงหิน", "health_zone": "4"},
                {"hospcode": "10675", "hosp_name": "รพ.สต.บางใหญ่", "province": "นนทบุรี", "district": "บางใหญ่", "subdistrict": "บางใหญ่", "health_zone": "4"},
                {"hospcode": "10981", "hosp_name": "รพ.อยุธยา", "province": "พระนครศรีอยุธยา", "district": "พระนครศรีอยุธยา", "subdistrict": "ประตูชัย", "health_zone": "4"},
                {"hospcode": "11475", "hosp_name": "รพ.สต.บ้านป้อม", "province": "พระนครศรีอยุธยา", "district": "พระนครศรีอยุธยา", "subdistrict": "บ้านป้อม", "health_zone": "4"},
                {"hospcode": "10682", "hosp_name": "รพ.นครพิงค์", "province": "เชียงใหม่", "district": "แม่ริม", "subdistrict": "ดอนแก้ว", "health_zone": "1"},
                {"hospcode": "10683", "hosp_name": "รพ.สันป่าตอง", "province": "เชียงใหม่", "district": "สันป่าตอง", "subdistrict": "ยุหว่า", "health_zone": "1"},
                {"hospcode": "10684", "hosp_name": "รพ.แม่ริม", "province": "เชียงใหม่", "district": "แม่ริม", "subdistrict": "ริมใต้", "health_zone": "1"},
                {"hospcode": "10685", "hosp_name": "รพ.สันทราย", "province": "เชียงใหม่", "district": "สันทราย", "subdistrict": "สันทรายน้อย", "health_zone": "1"},
                {"hospcode": "10686", "hosp_name": "รพ.หางดง", "province": "เชียงใหม่", "district": "หางดง", "subdistrict": "หางดง", "health_zone": "1"},
                {"hospcode": "10967", "hosp_name": "รพ.สวรรค์ประชารักษ์", "province": "นครสวรรค์", "district": "เมืองนครสวรรค์", "subdistrict": "ปากน้ำโพ", "health_zone": "3"},
                {"hospcode": "11120", "hosp_name": "รพ.เก้าเลี้ยว", "province": "นครสวรรค์", "district": "เก้าเลี้ยว", "subdistrict": "เก้าเลี้ยว", "health_zone": "3"},
                {"hospcode": "10969", "hosp_name": "รพ.ขอนแก่น", "province": "ขอนแก่น", "district": "เมืองขอนแก่น", "subdistrict": "ในเมือง", "health_zone": "7"},
                {"hospcode": "11045", "hosp_name": "รพ.กระนวน", "province": "ขอนแก่น", "district": "กระนวน", "subdistrict": "หนองโก", "health_zone": "7"},
                {"hospcode": "11412", "hosp_name": "รพ.สต.บ้านเป็ด", "province": "ขอนแก่น", "district": "เมืองขอนแก่น", "subdistrict": "บ้านเป็ด", "health_zone": "7"},
                {"hospcode": "10972", "hosp_name": "รพ.มหาราชนครราชสีมา", "province": "นครราชสีมา", "district": "เมืองนครราชสีมา", "subdistrict": "ในเมือง", "health_zone": "9"},
                {"hospcode": "10722", "hosp_name": "รพ.สต.จอหอ", "province": "นครราชสีมา", "district": "เมืองนครราชสีมา", "subdistrict": "จอหอ", "health_zone": "9"},
                {"hospcode": "10975", "hosp_name": "รพ.สุราษฎร์ธานี", "province": "สุราษฎร์ธานี", "district": "เมืองสุราษฎร์ธานี", "subdistrict": "ตลาด", "health_zone": "11"},
                {"hospcode": "11204", "hosp_name": "รพ.เกาะสมุย", "province": "สุราษฎร์ธานี", "district": "เกาะสมุย", "subdistrict": "อ่างทอง", "health_zone": "11"},
                {"hospcode": "10985", "hosp_name": "รพ.หาดใหญ่", "province": "สงขลา", "district": "หาดใหญ่", "subdistrict": "หาดใหญ่", "health_zone": "12"},
                {"hospcode": "10811", "hosp_name": "รพ.สต.พะวง", "province": "สงขลา", "district": "เมืองสงขลา", "subdistrict": "พะวง", "health_zone": "12"},
                {"hospcode": "20001", "hosp_name": "รพ.สต.ท่าทราย", "province": "นนทบุรี", "district": "ไทรน้อย", "subdistrict": "ท่าทราย", "health_zone": "4"},
                {"hospcode": "20002", "hosp_name": "รพ.สต.บ้านเลน", "province": "พระนครศรีอยุธยา", "district": "บางปะอิน", "subdistrict": "บ้านเลน", "health_zone": "4"},
                {"hospcode": "20003", "hosp_name": "รพ.สต.ศรีภูมิ", "province": "เชียงใหม่", "district": "หางดง", "subdistrict": "ศรีภูมิ", "health_zone": "1"},
                {"hospcode": "20004", "hosp_name": "รพ.สต.พยุหะ", "province": "นครสวรรค์", "district": "เมืองนครสวรรค์", "subdistrict": "พยุหะ", "health_zone": "3"},
                {"hospcode": "20005", "hosp_name": "รพ.สต.หนองโก", "province": "ขอนแก่น", "district": "น้ำพอง", "subdistrict": "หนองโก", "health_zone": "7"},
                {"hospcode": "20006", "hosp_name": "รพ.สต.เมืองปัก", "province": "นครราชสีมา", "district": "ปากช่อง", "subdistrict": "เมืองปัก", "health_zone": "9"},
                {"hospcode": "20007", "hosp_name": "รพ.สต.อ่างทอง", "province": "สุราษฎร์ธานี", "district": "เมืองสุราษฎร์ธานี", "subdistrict": "อ่างทอง", "health_zone": "11"},
                {"hospcode": "20008", "hosp_name": "รพ.สต.พะวง 2", "province": "สงขลา", "district": "เมืองสงขลา", "subdistrict": "พะวง", "health_zone": "12"},
                {"hospcode": "20009", "hosp_name": "รพ.สต.คลองเกลือ", "province": "นนทบุรี", "district": "เมืองนนทบุรี", "subdistrict": "คลองเกลือ", "health_zone": "4"},
                {"hospcode": "20010", "hosp_name": "รพ.สต.เสนา", "province": "พระนครศรีอยุธยา", "district": "บางไทร", "subdistrict": "เสนา", "health_zone": "4"},
                {"hospcode": "20011", "hosp_name": "รพ.สต.ศรีภูมิ 2", "province": "เชียงใหม่", "district": "หางดง", "subdistrict": "ศรีภูมิ", "health_zone": "1"},
                {"hospcode": "20012", "hosp_name": "รพ.สต.ลาดยาว", "province": "นครสวรรค์", "district": "ตาคลี", "subdistrict": "ลาดยาว", "health_zone": "3"},
                {"hospcode": "20013", "hosp_name": "รพ.สต.บึงเนียม", "province": "ขอนแก่น", "district": "ชุมแพ", "subdistrict": "บึงเนียม", "health_zone": "7"},
                {"hospcode": "20014", "hosp_name": "รพ.สต.เมืองปัก 2", "province": "นครราชสีมา", "district": "ด่านขุนทด", "subdistrict": "เมืองปัก", "health_zone": "9"},
                {"hospcode": "20015", "hosp_name": "รพ.สต.มะขามเตี้ย", "province": "สุราษฎร์ธานี", "district": "เกาะสมุย", "subdistrict": "มะขามเตี้ย", "health_zone": "11"},
                {"hospcode": "20016", "hosp_name": "รพ.สต.บ่อยาง", "province": "สงขลา", "district": "สะเดา", "subdistrict": "บ่อยาง", "health_zone": "12"},
                {"hospcode": "20017", "hosp_name": "รพ.สต.ท่าทราย 2", "province": "นนทบุรี", "district": "บางใหญ่", "subdistrict": "ท่าทราย", "health_zone": "4"},
                {"hospcode": "20018", "hosp_name": "รพ.สต.ท่าเรือ", "province": "พระนครศรีอยุธยา", "district": "วังน้อย", "subdistrict": "ท่าเรือ", "health_zone": "4"},
                {"hospcode": "20019", "hosp_name": "รพ.สต.ยางเนิ้ง", "province": "เชียงใหม่", "district": "สารภี", "subdistrict": "ยางเนิ้ง", "health_zone": "1"},
                {"hospcode": "20020", "hosp_name": "รพ.สต.พยุหะ 2", "province": "นครสวรรค์", "district": "เมืองนครสวรรค์", "subdistrict": "พยุหะ", "health_zone": "3"},
                {"hospcode": "20021", "hosp_name": "รพ.สต.ชุมแพ", "province": "ขอนแก่น", "district": "บ้านไผ่", "subdistrict": "ชุมแพ", "health_zone": "7"},
                {"hospcode": "20022", "hosp_name": "รพ.สต.ปากช่อง", "province": "นครราชสีมา", "district": "สีคิ้ว", "subdistrict": "ปากช่อง", "health_zone": "9"},
                {"hospcode": "20023", "hosp_name": "รพ.สต.คีรีรัฐ", "province": "สุราษฎร์ธานี", "district": "คีรีรัฐนิคม", "subdistrict": "คีรีรัฐ", "health_zone": "11"},
                {"hospcode": "20024", "hosp_name": "รพ.สต.ทุ่งตำเสา", "province": "สงขลา", "district": "ควนเนียง", "subdistrict": "ทุ่งตำเสา", "health_zone": "12"},
                {"hospcode": "20025", "hosp_name": "รพ.สต.ไทรน้อย", "province": "นนทบุรี", "district": "ปากเกร็ด", "subdistrict": "ไทรน้อย", "health_zone": "4"},
                {"hospcode": "20026", "hosp_name": "รพ.สต.ลุมพลี", "province": "พระนครศรีอยุธยา", "district": "บางปะอิน", "subdistrict": "ลุมพลี", "health_zone": "4"},
                {"hospcode": "20027", "hosp_name": "รพ.สต.ศรีภูมิ 2", "province": "เชียงใหม่", "district": "ดอยสะเก็ด", "subdistrict": "ศรีภูมิ", "health_zone": "1"},
                {"hospcode": "20028", "hosp_name": "รพ.สต.ชุมแสง", "province": "นครสวรรค์", "district": "ชุมแสง", "subdistrict": "ชุมแสง", "health_zone": "3"},
                {"hospcode": "20029", "hosp_name": "รพ.สต.เมืองพล", "province": "ขอนแก่น", "district": "น้ำพอง", "subdistrict": "เมืองพล", "health_zone": "7"},
                {"hospcode": "20030", "hosp_name": "รพ.สต.จอหอ 2", "province": "นครราชสีมา", "district": "เมืองนครราชสีมา", "subdistrict": "จอหอ", "health_zone": "9"},
                {"hospcode": "20031", "hosp_name": "รพ.สต.กาญจนดิษฐ์", "province": "สุราษฎร์ธานี", "district": "พุนพิน", "subdistrict": "กาญจนดิษฐ์", "health_zone": "11"},
                {"hospcode": "20032", "hosp_name": "รพ.สต.หาดใหญ่", "province": "สงขลา", "district": "จะนะ", "subdistrict": "หาดใหญ่", "health_zone": "12"},
                {"hospcode": "20033", "hosp_name": "รพ.สต.วัดชลอ", "province": "นนทบุรี", "district": "บางใหญ่", "subdistrict": "วัดชลอ", "health_zone": "4"},
                {"hospcode": "20034", "hosp_name": "รพ.สต.เสนา 2", "province": "พระนครศรีอยุธยา", "district": "พระนครศรีอยุธยา", "subdistrict": "เสนา", "health_zone": "4"},
                {"hospcode": "20035", "hosp_name": "รพ.สต.ช้างคลาน", "province": "เชียงใหม่", "district": "แม่ริม", "subdistrict": "ช้างคลาน", "health_zone": "1"},
                {"hospcode": "20036", "hosp_name": "รพ.สต.ปากน้ำโพ", "province": "นครสวรรค์", "district": "ตาคลี", "subdistrict": "ปากน้ำโพ", "health_zone": "3"},
                {"hospcode": "20037", "hosp_name": "รพ.สต.บ้านไผ่", "province": "ขอนแก่น", "district": "เมืองขอนแก่น", "subdistrict": "บ้านไผ่", "health_zone": "7"},
                {"hospcode": "20038", "hosp_name": "รพ.สต.เมืองปัก 2", "province": "นครราชสีมา", "district": "พิมาย", "subdistrict": "เมืองปัก", "health_zone": "9"},
                {"hospcode": "20039", "hosp_name": "รพ.สต.มะขามเตี้ย 2", "province": "สุราษฎร์ธานี", "district": "เมืองสุราษฎร์ธานี", "subdistrict": "มะขามเตี้ย", "health_zone": "11"},
                {"hospcode": "20040", "hosp_name": "รพ.สต.บ่อยาง 2", "province": "สงขลา", "district": "สิงหนคร", "subdistrict": "บ่อยาง", "health_zone": "12"},
                {"hospcode": "20041", "hosp_name": "รพ.สต.บางรักพัฒนา", "province": "นนทบุรี", "district": "บางกรวย", "subdistrict": "บางรักพัฒนา", "health_zone": "4"},
                {"hospcode": "20042", "hosp_name": "รพ.สต.ท่าเรือ 2", "province": "พระนครศรีอยุธยา", "district": "เสนา", "subdistrict": "ท่าเรือ", "health_zone": "4"},
                {"hospcode": "20043", "hosp_name": "รพ.สต.ช้างเผือก", "province": "เชียงใหม่", "district": "สารภี", "subdistrict": "ช้างเผือก", "health_zone": "1"},
                {"hospcode": "20044", "hosp_name": "รพ.สต.ตาคลี", "province": "นครสวรรค์", "district": "ชุมแสง", "subdistrict": "ตาคลี", "health_zone": "3"},
                {"hospcode": "20045", "hosp_name": "รพ.สต.หนองโก 2", "province": "ขอนแก่น", "district": "เมืองขอนแก่น", "subdistrict": "หนองโก", "health_zone": "7"},
                {"hospcode": "20046", "hosp_name": "รพ.สต.บ้านใหม่", "province": "นครราชสีมา", "district": "สีคิ้ว", "subdistrict": "บ้านใหม่", "health_zone": "9"},
                {"hospcode": "20047", "hosp_name": "รพ.สต.ตลาด", "province": "สุราษฎร์ธานี", "district": "เมืองสุราษฎร์ธานี", "subdistrict": "ตลาด", "health_zone": "11"},
                {"hospcode": "20048", "hosp_name": "รพ.สต.คอหงส์", "province": "สงขลา", "district": "สะเดา", "subdistrict": "คอหงส์", "health_zone": "12"},
                {"hospcode": "20049", "hosp_name": "รพ.สต.พิมลราช", "province": "นนทบุรี", "district": "ปากเกร็ด", "subdistrict": "พิมลราช", "health_zone": "4"},
                {"hospcode": "20050", "hosp_name": "รพ.สต.บ่อโพง", "province": "พระนครศรีอยุธยา", "district": "บางไทร", "subdistrict": "บ่อโพง", "health_zone": "4"},
                {"hospcode": "20051", "hosp_name": "รพ.สต.สันทรายน้อย", "province": "เชียงใหม่", "district": "ดอยสะเก็ด", "subdistrict": "สันทรายน้อย", "health_zone": "1"},
                {"hospcode": "20052", "hosp_name": "รพ.สต.ตาคลี 2", "province": "นครสวรรค์", "district": "ลาดยาว", "subdistrict": "ตาคลี", "health_zone": "3"},
                {"hospcode": "20053", "hosp_name": "รพ.สต.ในเมือง", "province": "ขอนแก่น", "district": "พล", "subdistrict": "ในเมือง", "health_zone": "7"},
                {"hospcode": "20054", "hosp_name": "รพ.สต.ในเมือง 2", "province": "นครราชสีมา", "district": "เมืองนครราชสีมา", "subdistrict": "ในเมือง", "health_zone": "9"},
                {"hospcode": "20055", "hosp_name": "รพ.สต.ลิปะน้อย", "province": "สุราษฎร์ธานี", "district": "เมืองสุราษฎร์ธานี", "subdistrict": "ลิปะน้อย", "health_zone": "11"},
                {"hospcode": "20056", "hosp_name": "รพ.สต.ชิงโค", "province": "สงขลา", "district": "เมืองสงขลา", "subdistrict": "ชิงโค", "health_zone": "12"},
                {"hospcode": "20057", "hosp_name": "รพ.สต.บางตลาด", "province": "นนทบุรี", "district": "เมืองนนทบุรี", "subdistrict": "บางตลาด", "health_zone": "4"},
                {"hospcode": "20058", "hosp_name": "รพ.สต.กะมัง", "province": "พระนครศรีอยุธยา", "district": "พระนครศรีอยุธยา", "subdistrict": "กะมัง", "health_zone": "4"},
                {"hospcode": "20059", "hosp_name": "รพ.สต.ศรีภูมิ 2", "province": "เชียงใหม่", "district": "เมืองเชียงใหม่", "subdistrict": "ศรีภูมิ", "health_zone": "1"},
                {"hospcode": "20060", "hosp_name": "รพ.สต.ชุมแสง 2", "province": "นครสวรรค์", "district": "เก้าเลี้ยว", "subdistrict": "ชุมแสง", "health_zone": "3"},
                {"hospcode": "20061", "hosp_name": "รพ.สต.ในเมือง 2", "province": "ขอนแก่น", "district": "บ้านไผ่", "subdistrict": "ในเมือง", "health_zone": "7"},
                {"hospcode": "20062", "hosp_name": "รพ.สต.ในเมืองพิมาย", "province": "นครราชสีมา", "district": "ปากช่อง", "subdistrict": "ในเมืองพิมาย", "health_zone": "9"},
                {"hospcode": "20063", "hosp_name": "รพ.สต.ดอนสัก", "province": "สุราษฎร์ธานี", "district": "พุนพิน", "subdistrict": "ดอนสัก", "health_zone": "11"},
                {"hospcode": "20064", "hosp_name": "รพ.สต.ควนเนียง", "province": "สงขลา", "district": "สิงหนคร", "subdistrict": "ควนเนียง", "health_zone": "12"},
                {"hospcode": "20065", "hosp_name": "รพ.สต.ไทรน้อย 2", "province": "นนทบุรี", "district": "เมืองนนทบุรี", "subdistrict": "ไทรน้อย", "health_zone": "4"},
                {"hospcode": "20066", "hosp_name": "รพ.สต.กะมัง 2", "province": "พระนครศรีอยุธยา", "district": "ท่าเรือ", "subdistrict": "กะมัง", "health_zone": "4"},
                {"hospcode": "20067", "hosp_name": "รพ.สต.ยางเนิ้ง 2", "province": "เชียงใหม่", "district": "ดอยสะเก็ด", "subdistrict": "ยางเนิ้ง", "health_zone": "1"},
                {"hospcode": "20068", "hosp_name": "รพ.สต.เก้าเลี้ยว", "province": "นครสวรรค์", "district": "เมืองนครสวรรค์", "subdistrict": "เก้าเลี้ยว", "health_zone": "3"},
                {"hospcode": "20069", "hosp_name": "รพ.สต.วังชัย", "province": "ขอนแก่น", "district": "กระนวน", "subdistrict": "วังชัย", "health_zone": "7"},
                {"hospcode": "20070", "hosp_name": "รพ.สต.โคกกรวด", "province": "นครราชสีมา", "district": "ปักธงชัย", "subdistrict": "โคกกรวด", "health_zone": "9"},
                {"hospcode": "20071", "hosp_name": "รพ.สต.วัดประดู่", "province": "สุราษฎร์ธานี", "district": "กาญจนดิษฐ์", "subdistrict": "วัดประดู่", "health_zone": "11"},
                {"hospcode": "20072", "hosp_name": "รพ.สต.พะวง 2", "province": "สงขลา", "district": "สะเดา", "subdistrict": "พะวง", "health_zone": "12"},
                {"hospcode": "20073", "hosp_name": "รพ.สต.คลองเกลือ 2", "province": "นนทบุรี", "district": "บางใหญ่", "subdistrict": "คลองเกลือ", "health_zone": "4"},
                {"hospcode": "20074", "hosp_name": "รพ.สต.บางพลี", "province": "พระนครศรีอยุธยา", "district": "เสนา", "subdistrict": "บางพลี", "health_zone": "4"},
                {"hospcode": "20075", "hosp_name": "รพ.สต.หางดง", "province": "เชียงใหม่", "district": "เมืองเชียงใหม่", "subdistrict": "หางดง", "health_zone": "1"},
                {"hospcode": "20076", "hosp_name": "รพ.สต.นครสวรรค์ตก", "province": "นครสวรรค์", "district": "เมืองนครสวรรค์", "subdistrict": "นครสวรรค์ตก", "health_zone": "3"},
                {"hospcode": "20077", "hosp_name": "รพ.สต.บ้านไผ่ 2", "province": "ขอนแก่น", "district": "กระนวน", "subdistrict": "บ้านไผ่", "health_zone": "7"},
                {"hospcode": "20078", "hosp_name": "รพ.สต.ในเมืองพิมาย 2", "province": "นครราชสีมา", "district": "พิมาย", "subdistrict": "ในเมืองพิมาย", "health_zone": "9"},
                {"hospcode": "20079", "hosp_name": "รพ.สต.ท่าข้าม", "province": "สุราษฎร์ธานี", "district": "คีรีรัฐนิคม", "subdistrict": "ท่าข้าม", "health_zone": "11"},
                {"hospcode": "20080", "hosp_name": "รพ.สต.ทุ่งตำเสา 2", "province": "สงขลา", "district": "ควนเนียง", "subdistrict": "ทุ่งตำเสา", "health_zone": "12"},
                {"hospcode": "20081", "hosp_name": "รพ.สต.ท่าทราย 2", "province": "นนทบุรี", "district": "บางใหญ่", "subdistrict": "ท่าทราย", "health_zone": "4"},
                {"hospcode": "20082", "hosp_name": "รพ.สต.คลองสวนพลู", "province": "พระนครศรีอยุธยา", "district": "พระนครศรีอยุธยา", "subdistrict": "คลองสวนพลู", "health_zone": "4"},
                {"hospcode": "20083", "hosp_name": "รพ.สต.เชิงดอย", "province": "เชียงใหม่", "district": "สันป่าตอง", "subdistrict": "เชิงดอย", "health_zone": "1"},
                {"hospcode": "20084", "hosp_name": "รพ.สต.ลาดยาว 2", "province": "นครสวรรค์", "district": "ชุมแสง", "subdistrict": "ลาดยาว", "health_zone": "3"},
                {"hospcode": "20085", "hosp_name": "รพ.สต.ศิลา", "province": "ขอนแก่น", "district": "เมืองขอนแก่น", "subdistrict": "ศิลา", "health_zone": "7"},
                {"hospcode": "20086", "hosp_name": "รพ.สต.ในเมือง 2", "province": "นครราชสีมา", "district": "เมืองนครราชสีมา", "subdistrict": "ในเมือง", "health_zone": "9"},
                {"hospcode": "20087", "hosp_name": "รพ.สต.อ่างทอง 2", "province": "สุราษฎร์ธานี", "district": "พุนพิน", "subdistrict": "อ่างทอง", "health_zone": "11"},
                {"hospcode": "20088", "hosp_name": "รพ.สต.ทุ่งตำเสา 2", "province": "สงขลา", "district": "จะนะ", "subdistrict": "ทุ่งตำเสา", "health_zone": "12"}
            ]
            df_mock = pd.DataFrame(mock_locs)
            df_mock.to_sql('health_facilities_master', con=engine, if_exists='append', index=False)
            print(f"✅ นำเข้ารายการจำลอง {len(df_mock)} แห่งเพื่อใช้เป็นหน่วยบริการอ้างอิงเสร็จสิ้น!")
    except Exception as e:
        print(f"❌ Error seeding health facilities master: {e}")

# Mapping หัวตารางภาษาไทย สำหรับ Excel Upsert
COLUMN_MAP_REV = {
    'รหัสหน่วยบริการ': 'hospcode', 'รหัส 5 หลัก': 'hospcode', 'ชื่อหน่วยบริการ': 'hosp_name', 'ปีงบประมาณ': 'fiscal_year',
    'ภาค': 'region', 'เขตสุขภาพ': 'health_zone', 'จังหวัด': 'province', 'อำเภอ': 'district', 'ตำบล': 'subdistrict',
    'จำนวนเด็กทั้งหมด': 'total_kids', 'จำนวนตรวจ': 'screened_kids', 'พบฟันตกกระ': 'fluorosis_cases',
    'ร้อยละเด็กฟันตกกระ': 'pct_fluorosis', 'severe_cases': 'severe_cases', 'สถานการณ์': 'status',
    
    'ชนิดน้ำ': 'water_type', 'สถานที่เก็บ': 'location_name', 'ปริมาณฟลูออไรด์': 'fluoride_level', 
    'ว/ด/ป ที่เก็บ': 'check_date', 'บ้านเลขที่': 'house_no', 'หมู่ที่': 'moo',
    'ละติจูด': 'latitude', 'ลองจิจูด': 'longitude', 'หมายเหตุ': 'remark', 'แหล่งข้อมูล': 'data_source'
}

VALID_DB_COLUMNS = [
    'hospcode', 'hosp_name', 'fiscal_year', 'region', 'health_zone', 'province', 'district', 'subdistrict',
    'total_kids', 'screened_kids', 'fluorosis_cases', 'pct_fluorosis', 'severe_cases', 'dean_index_status', 'status',
    'water_type', 'location_name', 'fluoride_level', 'check_date', 'house_no', 'moo', 'latitude', 'longitude',
    'remark', 'data_source'
]

init_database_tables()
seed_health_facilities_master()

def safe_extract(df, col_name, default_val):
    return df[col_name] if col_name in df.columns else default_val

DISTRICT_CENTROIDS_CACHE = None

def get_district_centroids():
    global DISTRICT_CENTROIDS_CACHE
    if DISTRICT_CENTROIDS_CACHE is not None:
        return DISTRICT_CENTROIDS_CACHE
        
    centroids = {}
    try:
        with engine.connect() as conn:
            # Water records
            rows_w = conn.execute(text("""
                SELECT `province`, `district`, AVG(`latitude`), AVG(`longitude`)
                FROM `water_records`
                WHERE `latitude` != 0.0 AND `latitude` IS NOT NULL AND `longitude` != 0.0 AND `longitude` IS NOT NULL
                GROUP BY `province`, `district`
            """)).fetchall()
            for r in rows_w:
                prov = str(r[0]).strip()
                dist = str(r[1]).strip()
                centroids[(prov, dist)] = (float(r[2]), float(r[3]))
                
            # Dental records
            rows_d = conn.execute(text("""
                SELECT `province`, `district`, AVG(`latitude`), AVG(`longitude`)
                FROM `dental_records`
                WHERE `latitude` != 0.0 AND `latitude` IS NOT NULL AND `longitude` != 0.0 AND `longitude` IS NOT NULL
                GROUP BY `province`, `district`
            """)).fetchall()
            for r in rows_d:
                prov = str(r[0]).strip()
                dist = str(r[1]).strip()
                if (prov, dist) not in centroids:
                    centroids[(prov, dist)] = (float(r[2]), float(r[3]))
    except Exception as e:
        print(f"⚠️ Error building centroid lookup: {e}")
        
    province_centroids = {}
    for (prov, dist), (lat, lng) in centroids.items():
        if prov not in province_centroids:
            province_centroids[prov] = []
        province_centroids[prov].append((lat, lng))
        
    DISTRICT_CENTROIDS_CACHE = {
        'districts': centroids,
        'provinces': {p: (float(np.mean([x[0] for x in coords])), float(np.mean([x[1] for x in coords]))) for p, coords in province_centroids.items() if coords}
    }
    return DISTRICT_CENTROIDS_CACHE

def load_data_from_db(load_water=True, load_dental=True, filters=None):
    df_w, df_d = pd.DataFrame(), pd.DataFrame()
    filters = filters or {}
    
    water_filter_map = {
        'ภาค': 'region',
        'เขตสุขภาพ': 'health_zone',
        'จังหวัด': 'province',
        'อำเภอ': 'district',
        'ตำบล': 'subdistrict'
    }
    
    dental_filter_map = {
        'ปี': 'fiscal_year',
        'ภาค': 'region',
        'เขตสุขภาพ': 'health_zone',
        'จังหวัด': 'province',
        'อำเภอ': 'district',
        'ตำบล': 'subdistrict'
    }
    
    if load_water:
        try:
            sql = "SELECT * FROM `water_records` WHERE 1=1"
            params = {}
            for api_key, col in water_filter_map.items():
                val = filters.get(api_key)
                if val and val != 'ทั้งหมด':
                    sql += f" AND `{col}` = :{col}"
                    params[col] = str(val).strip()
            
            y_val = filters.get('ปี')
            if y_val and y_val != 'ทั้งหมด':
                sql += " AND `check_date` LIKE :check_date_like"
                params['check_date_like'] = f"{str(y_val).strip()}%"
                
            with engine.connect() as conn:
                w_raw = pd.read_sql(text(sql), conn, params=params)
                
            
            if not w_raw.empty:
                w_raw['check_date_parsed'] = pd.to_datetime(w_raw['check_date'], errors='coerce')
                w_raw = w_raw.sort_values('check_date_parsed', ascending=False).drop_duplicates(subset=['location_name', 'latitude', 'longitude'])
                
                df_w = pd.DataFrame(index=w_raw.index)

                dates = pd.to_datetime(w_raw['check_date'], errors='coerce')
                df_w['วันที่ตรวจ'] = dates.dt.strftime('%Y-%m-%d').fillna('')
                df_w['ว/ด/ป ที่เก็บ'] = df_w['วันที่ตรวจ']
                df_w['ปี'] = dates.dt.strftime('%Y').fillna('') # สำหรับ Filter
                
                df_w['ภาค'] = safe_extract(w_raw, 'region', 'ไม่ระบุ')
                df_w['เขตสุขภาพ'] = safe_extract(w_raw, 'health_zone', 'ไม่ระบุ')
                df_w['จังหวัด'] = safe_extract(w_raw, 'province', 'ไม่ระบุ')
                df_w['อำเภอ'] = safe_extract(w_raw, 'district', 'ไม่ระบุ')
                df_w['ตำบล'] = safe_extract(w_raw, 'subdistrict', 'ไม่ระบุ')
                df_w['สถานที่เก็บ'] = safe_extract(w_raw, 'location_name', 'ไม่ระบุ')
                df_w['ชนิดน้ำ'] = safe_extract(w_raw, 'water_type', 'ไม่ระบุ')
                df_w['กลุ่มแหล่งน้ำ'] = safe_extract(w_raw, 'water_category', 'ไม่ระบุ')
                df_w['ปริมาณฟลูออไรด์'] = pd.to_numeric(safe_extract(w_raw, 'fluoride_level', 0.0), errors='coerce').fillna(0.0)
                df_w['สถานการณ์'] = safe_extract(w_raw, 'status', 'ไม่ระบุ')
                df_w['บ้านเลขที่'] = safe_extract(w_raw, 'house_no', '-')
                df_w['หมู่ที่'] = safe_extract(w_raw, 'moo', '-')
                df_w['หมายเหตุ'] = safe_extract(w_raw, 'remark', '-')
                df_w['แหล่งข้อมูล'] = safe_extract(w_raw, 'data_source', '-')
                
                # Impute missing coordinates
                centroids = get_district_centroids()
                lats, lngs = [], []
                for _, r in w_raw.iterrows():
                    lat = pd.to_numeric(r.get('latitude', 0.0), errors='coerce')
                    lng = pd.to_numeric(r.get('longitude', 0.0), errors='coerce')
                    if pd.isna(lat) or pd.isna(lng) or lat == 0.0 or lng == 0.0:
                        prov = str(r.get('province', '')).strip()
                        dist = str(r.get('district', '')).strip()
                        fallback = centroids['districts'].get((prov, dist)) or centroids['provinces'].get(prov) or (13.0, 101.5)
                        lat, lng = fallback[0], fallback[1]
                    lats.append(lat)
                    lngs.append(lng)
                df_w['ละติจูด'] = lats
                df_w['ลองจิจูด'] = lngs
        except Exception as e: print(f"⚠️ Water DB Error: {e}")

    if load_dental:
        try:
            sql = "SELECT * FROM `dental_records` WHERE 1=1"
            params = {}
            for api_key, col in dental_filter_map.items():
                val = filters.get(api_key)
                if val and val != 'ทั้งหมด':
                    sql += f" AND `{col}` = :{col}"
                    params[col] = str(val).strip()
                    
            with engine.connect() as conn:
                d_raw = pd.read_sql(text(sql), conn, params=params)
                
            if not d_raw.empty:
                df_d = pd.DataFrame(index=d_raw.index)
                df_d['ปีงบประมาณ'] = safe_extract(d_raw, 'fiscal_year', 'ไม่ระบุ')
                df_d['ปี'] = df_d['ปีงบประมาณ']
                
                df_d['ภาค'] = safe_extract(d_raw, 'region', 'ไม่ระบุ')
                df_d['เขตสุขภาพ'] = safe_extract(d_raw, 'health_zone', 'ไม่ระบุ')
                df_d['จังหวัด'] = safe_extract(d_raw, 'province', 'ไม่ระบุ')
                df_d['อำเภอ'] = safe_extract(d_raw, 'district', 'ไม่ระบุ')
                df_d['ตำบล'] = safe_extract(d_raw, 'subdistrict', 'ไม่ระบุ')
                df_d['รหัสหน่วยบริการ'] = safe_extract(d_raw, 'hospcode', 'ไม่ระบุ')
                df_d['ชื่อหน่วยบริการ'] = safe_extract(d_raw, 'hosp_name', 'ไม่ระบุ')
                df_d['จำนวนเด็กทั้งหมด'] = pd.to_numeric(safe_extract(d_raw, 'total_kids', 0), errors='coerce').fillna(0)
                df_d['จำนวนตรวจ'] = pd.to_numeric(safe_extract(d_raw, 'screened_kids', 0), errors='coerce').fillna(0)
                df_d['พบฟันตกกระ'] = pd.to_numeric(safe_extract(d_raw, 'fluorosis_cases', 0), errors='coerce').fillna(0)
                df_d['ร้อยละเด็กฟันตกกระ'] = pd.to_numeric(safe_extract(d_raw, 'pct_fluorosis', 0.0), errors='coerce').fillna(0)
                df_d['severe_cases'] = pd.to_numeric(safe_extract(d_raw, 'severe_cases', 0), errors='coerce').fillna(0)
                
                s_col = d_raw['dean_index_status'] if 'dean_index_status' in d_raw.columns else d_raw.get('status', pd.Series(['ปกติ (Normal)']*len(d_raw)))
                dean_map = {'Normal': 'ปกติ (Normal)', 'Very Mild': 'ระดับอ่อนมาก (Very Mild)', 'Mild': 'ระดับอ่อน (Mild)', 'Moderate': 'ระดับปานกลาง (Moderate)', 'Severe': 'ระดับรุนแรง (Severe)'}
                df_d['สถานการณ์'] = s_col.replace(dean_map)
                df_d['ประเภทแหล่งน้ำ'] = 'สภาวะฟันตกกระ (เด็ก)'
                
                # Impute missing coordinates
                centroids = get_district_centroids()
                lats, lngs = [], []
                for _, r in d_raw.iterrows():
                    lat = pd.to_numeric(r.get('latitude', 0.0), errors='coerce')
                    lng = pd.to_numeric(r.get('longitude', 0.0), errors='coerce')
                    if pd.isna(lat) or pd.isna(lng) or lat == 0.0 or lng == 0.0:
                        prov = str(r.get('province', '')).strip()
                        dist = str(r.get('district', '')).strip()
                        fallback = centroids['districts'].get((prov, dist)) or centroids['provinces'].get(prov) or (13.0, 101.5)
                        lat, lng = fallback[0], fallback[1]
                    lats.append(lat)
                    lngs.append(lng)
                df_d['ละติจูด'] = lats
                df_d['ลองจิจูด'] = lngs
        except Exception as e: print(f"⚠️ Dental DB Error: {e}")
        
    return df_w, df_d

def get_cat(name):
    try:
        with engine.connect() as conn:
            res = conn.execute(text("SELECT category FROM report_schemas WHERE report_name = :n"), {"n": name}).fetchone()
            return res[0] if res else ('health' if 'ตกกระ' in name else 'env')
    except: return 'env'

def natural_keys(t): return [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', str(t))]

# ==========================================
# 2. API Routes
# ==========================================
@app.route('/')
def home(): 
    return render_template('landing.html')

@app.route('/dashboard')
def dashboard(): 
    return render_template('index.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    try:
        username = data['username'].strip()
        password = data['password']
        fullname = data.get('fullname', '')
        role = data.get('role', 'local')
        p_hash = hashlib.sha256(password.encode()).hexdigest()
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO `admin_users` (username, password_hash, role, fullname, status) VALUES (:u, :p, :r, :f, 'pending')"), {"u": username, "p": p_hash, "r": role, "f": fullname})
        return jsonify({'success': True, 'message': 'ลงทะเบียนสำเร็จ กรุณารอผู้ดูแลระบบอนุมัติ'})
    except Exception as e:
        if 'Duplicate entry' in str(e):
            return jsonify({'success': False, 'message': 'ชื่อผู้ใช้งานนี้ถูกใช้ไปแล้ว'})
        return jsonify({'success': False, 'message': f'เกิดข้อผิดพลาด: {str(e)}'})

@app.route('/api/admin/users', methods=['GET'])
def admin_get_users():
    try:
        with engine.connect() as conn:
            res = conn.execute(text("SELECT id, username, fullname, role, status, created_at FROM `admin_users`")).fetchall()
            users = [dict(r._mapping) for r in res]
            return jsonify({'success': True, 'users': users})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/admin/users/approve', methods=['POST'])
def admin_approve_user():
    data = request.json
    try:
        user_id = data['id']
        action = data['action'] # 'approve' or 'reject'
        status = 'approved' if action == 'approve' else 'rejected'
        with engine.begin() as conn:
            conn.execute(text("UPDATE `admin_users` SET status = :s WHERE id = :id"), {"s": status, "id": user_id})
        return jsonify({'success': True, 'message': 'อัปเดตสถานะสำเร็จ'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/location_history', methods=['POST'])
def location_history():
    data = request.json
    location_name = data.get('location_name')
    lat = data.get('latitude')
    lng = data.get('longitude')
    try:
        with engine.connect() as conn:
            sql = "SELECT check_date, fluoride_level FROM water_records WHERE location_name = :loc AND latitude = :lat AND longitude = :lng ORDER BY check_date ASC"
            res = conn.execute(text(sql), {"loc": location_name, "lat": lat, "lng": lng}).fetchall()
            history = [{"date": r[0], "ppm": r[1]} for r in res]
            return jsonify({'success': True, 'history': history})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username', 'admin').strip()
    password = data.get('password', '')
    p_hash = hashlib.sha256(password.encode()).hexdigest()
    try:
        with engine.connect() as conn:
            res = conn.execute(text("SELECT password_hash, role, status FROM `admin_users` WHERE username = :u"), {"u": username}).fetchone()
            if res and res[0] == p_hash:
                if res[2] == 'pending':
                    return jsonify({'success': False, 'message': 'บัญชีของคุณอยู่ระหว่างรออนุมัติจากผู้ดูแลระบบ'})
                if res[2] == 'rejected':
                    return jsonify({'success': False, 'message': 'บัญชีของคุณถูกระงับการใช้งาน'})
                
                log_audit(username, 'LOGIN', 'SYSTEM', 'เข้าสู่ระบบสำเร็จ')
                return jsonify({'success': True, 'token': f"{username}:{p_hash}", 'role': res[1]})
            else:
                return jsonify({'success': False, 'message': 'ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'เกิดข้อผิดพลาดในการเชื่อมต่อ: {str(e)}'})

@app.route('/api/data', methods=['POST'])
def get_data():
    filters = request.json
    req_type = filters.get('type', 'ทั้งหมด')
    
    if req_type == 'home_summary' or req_type == 'ทั้งหมด':
        df_water, df_dental = load_data_from_db(load_water=True, load_dental=True, filters=filters)
    else:
        is_dental_request = (get_cat(req_type) == 'health')
        if is_dental_request:
            df_water, df_dental = load_data_from_db(load_water=False, load_dental=True, filters=filters)
        else:
            df_water, df_dental = load_data_from_db(load_water=True, load_dental=False, filters=filters)
    
    if req_type == 'home_summary' or req_type == 'ทั้งหมด':
        w_tot = len(df_water)
        w_over = len(df_water[df_water['สถานการณ์'] == 'เกินมาตรฐาน']) if w_tot > 0 else 0
        w_pct = round((w_over/w_tot)*100, 1) if w_tot > 0 else 0
        d_scr = int(df_dental['จำนวนตรวจ'].sum()) if not df_dental.empty else 0
        d_flu = int(df_dental['พบฟันตกกระ'].sum()) if not df_dental.empty else 0
        d_pct = round((d_flu/d_scr)*100, 1) if d_scr > 0 else 0
        
        red_zones = 0; top_alerts = []
        num_provinces = 0
        if not df_water.empty:
            prov_grp = df_water.groupby(['จังหวัด', 'เขตสุขภาพ'])
            prov_stats = []
            for name, grp in prov_grp:
                t = len(grp); o = len(grp[grp['สถานการณ์'] == 'เกินมาตรฐาน'])
                p = round((o/t)*100, 1) if t > 0 else 0
                if p > 10: red_zones += 1
                prov_stats.append({'prov': name[0], 'zone': name[1], 'pct': p})
            top_alerts = sorted(prov_stats, key=lambda x: x['pct'], reverse=True)[:5]
            num_provinces = len(prov_stats)
            
        safe_zones = num_provinces - red_zones if w_tot > 0 else 0
        zones = sorted(df_water['เขตสุขภาพ'].dropna().unique().tolist(), key=natural_keys) if not df_water.empty else []
        corr_labels = [f"เขต {z}" for z in zones]
        bar_data = []; line_data = []
        for z in zones:
            z_w = df_water[df_water['เขตสุขภาพ'] == str(z)]
            bar_data.append(round(z_w['ปริมาณฟลูออไรด์'].mean(), 2) if not z_w.empty else 0)
            z_d = df_dental[df_dental['เขตสุขภาพ'] == str(z)]
            zs = z_d['จำนวนตรวจ'].sum() if not z_d.empty else 0
            zf = z_d['พบฟันตกกระ'].sum() if not z_d.empty else 0
            line_data.append(round((zf/zs)*100, 1) if zs > 0 else 0)
 
        # ดึง Schema หน้าหลักส่งไปให้ Frontend จัดการ Dynamic KPIs
        home_schema_res = engine.connect().execute(text("SELECT schema_data FROM report_schemas WHERE report_name = 'หน้าหลัก'")).fetchone()
        home_config = json.loads(home_schema_res[0])['config'] if home_schema_res else {}
        base_vals = {'w_pct': w_pct, 'd_pct': d_pct, 'red_zones': red_zones, 'safe_zones': safe_zones, 'w_tot': w_tot, 'd_scr': d_scr, 'd_flu': d_flu}
        
        home_kpis_dynamic = []
        for k in home_config.get('kpis', []):
            c_val = base_vals.get(k.get('col', ''), 0)
            fmt_val = f"{c_val}%" if 'pct' in k.get('col', '') else c_val
            home_kpis_dynamic.append({'label': k.get('label', ''), 'value': fmt_val, 'color': k.get('color', 'main'), 'col': k.get('col', '')})
 
        water_points = []
        if not df_water.empty:
            water_valid = df_water[(df_water['ละติจูด'] != 0.0) & (df_water['ลองจิจูด'] != 0.0)]
            for _, r in water_valid.iterrows():
                water_points.append({
                    'name': str(r['สถานที่เก็บ']),
                    'lat': float(r['ละติจูด']),
                    'lng': float(r['ลองจิจูด']),
                    'val': float(r['ปริมาณฟลูออไรด์']),
                    'type': 'water',
                    'water_type': str(r.get('ชนิดน้ำ', 'ไม่ระบุ')),
                    'check_date': str(r.get('วันที่ตรวจ', '-')),
                    'category': str(r.get('กลุ่มแหล่งน้ำ', 'ไม่ระบุ')),
                    'prov': str(r['จังหวัด']),
                    'dist': str(r['อำเภอ']),
                    'subdist': str(r['ตำบล']),
                    'status': str(r['สถานการณ์']),
                    'detail': f"ปริมาณฟลูออไรด์ {r['ปริมาณฟลูออไรด์']} mg/L"
                })
        dental_points = []
        if not df_dental.empty:
            dental_valid = df_dental[(df_dental['ร้อยละเด็กฟันตกกระ'].notnull()) & (df_dental['ละติจูด'] != 0.0) & (df_dental['ลองจิจูด'] != 0.0)]
            for _, r in dental_valid.iterrows():
                dental_points.append({
                    'name': str(r['ชื่อหน่วยบริการ']),
                    'lat': float(r['ละติจูด']),
                    'lng': float(r['ลองจิจูด']),
                    'val': float(r['ร้อยละเด็กฟันตกกระ']),
                    'type': 'dental',
                    'category': 'dental',
                    'prov': str(r['จังหวัด']),
                    'dist': str(r['อำเภอ']),
                    'subdist': str(r['ตำบล']),
                    'status': str(r['สถานการณ์']),
                    'detail': f"ฟันตกกระ {r['ร้อยละเด็กฟันตกกระ']}%"
                })
 
        # Cascading dropdown logic for home summary
        raw_w, raw_d = load_data_from_db(load_water=True, load_dental=True)
        df_w_geo = raw_w[['ปี', 'ภาค', 'เขตสุขภาพ', 'จังหวัด', 'อำเภอ', 'ตำบล']].dropna(how='all') if not raw_w.empty else pd.DataFrame()
        df_d_geo = raw_d[['ปี', 'ภาค', 'เขตสุขภาพ', 'จังหวัด', 'อำเภอ', 'ตำบล']].dropna(how='all') if not raw_d.empty else pd.DataFrame()
        
        if not df_w_geo.empty and not df_d_geo.empty:
            base_df = pd.concat([df_w_geo, df_d_geo], ignore_index=True)
        elif not df_w_geo.empty:
            base_df = df_w_geo
        else:
            base_df = df_d_geo
            
        years_list = sorted(list(set([str(x) for x in base_df['ปี'].dropna().unique() if x])), reverse=True)
        regions_list = sorted(list(set([str(x) for x in base_df['ภาค'].dropna().unique() if x])))
        
        df_zone_temp = base_df.copy()
        r_val = filters.get('ภาค')
        if r_val and r_val != 'ทั้งหมด':
            df_zone_temp = df_zone_temp[df_zone_temp['ภาค'].astype(str).str.strip() == str(r_val).strip()]
        zones_list = sorted(list(set([str(x) for x in df_zone_temp['เขตสุขภาพ'].dropna().unique() if x])), key=natural_keys)
        
        df_prov_temp = df_zone_temp.copy()
        z_val = filters.get('เขตสุขภาพ')
        if z_val and z_val != 'ทั้งหมด':
            df_prov_temp = df_prov_temp[df_prov_temp['เขตสุขภาพ'].astype(str).str.strip() == str(z_val).strip()]
        provinces_list = sorted(list(set([str(x) for x in df_prov_temp['จังหวัด'].dropna().unique() if x])))
        
        df_dist_temp = df_prov_temp.copy()
        p_val = filters.get('จังหวัด')
        if p_val and p_val != 'ทั้งหมด':
            df_dist_temp = df_dist_temp[df_dist_temp['จังหวัด'].astype(str).str.strip() == str(p_val).strip()]
        districts_list = sorted(list(set([str(x) for x in df_dist_temp['อำเภอ'].dropna().unique() if x])))
        
        df_subdist_temp = df_dist_temp.copy()
        d_val = filters.get('อำเภอ')
        if d_val and d_val != 'ทั้งหมด':
            df_subdist_temp = df_subdist_temp[df_subdist_temp['อำเภอ'].astype(str).str.strip() == str(d_val).strip()]
        subdistricts_list = sorted(list(set([str(x) for x in df_subdist_temp['ตำบล'].dropna().unique() if x])))
        
        dropdowns = {
            'years': ['ทั้งหมด'] + years_list,
            'regions': ['ทั้งหมด'] + regions_list,
            'zones': ['ทั้งหมด'] + zones_list,
            'provinces': ['ทั้งหมด'] + provinces_list,
            'districts': ['ทั้งหมด'] + districts_list,
            'subdistricts': ['ทั้งหมด'] + subdistricts_list
        }

        return jsonify({
            'success': True,
            'home_kpis_dynamic': home_kpis_dynamic,
            'home_charts': {
                'donut': {
                    'labels': df_water['ชนิดน้ำ'].value_counts().index.tolist() if not df_water.empty else [],
                    'data': df_water['ชนิดน้ำ'].value_counts().tolist() if not df_water.empty else []
                },
                'corr': {
                    'labels': corr_labels,
                    'bar': bar_data,
                    'line': line_data
                }
            },
            'top_alerts': top_alerts,
            'water_points': water_points,
            'dental_points': dental_points,
            'dropdowns': dropdowns
        })
 
    is_dental = (get_cat(req_type) == 'health')
    df_filtered = df_dental.copy() if is_dental else df_water.copy()
 
    if df_filtered.empty: 
        return jsonify({'dropdowns': {'years': ['ทั้งหมด'], 'regions': ['ทั้งหมด'], 'zones': ['ทั้งหมด'], 'provinces': ['ทั้งหมด'], 'districts': ['ทั้งหมด'], 'subdistricts': ['ทั้งหมด']}, 'table_data': []})
 
    if not is_dental and req_type != 'ทั้งหมด':
        search_term = req_type.replace('คุณภาพ', '').strip()
        df_filtered = df_filtered[df_filtered['ชนิดน้ำ'].astype(str).str.contains(search_term, na=False)]
 
    for key in ['ปี', 'ภาค', 'เขตสุขภาพ', 'จังหวัด', 'อำเภอ', 'ตำบล']:
        val = filters.get(key)
        if val and val != 'ทั้งหมด':
            df_filtered = df_filtered[df_filtered[key].astype(str).str.strip() == str(val).strip()]
 
    base_df = df_dental if is_dental else df_water
    
    # Cascading dropdown logic for specific reports
    years_list = sorted([str(x) for x in base_df['ปี'].dropna().unique() if x], reverse=True)
    regions_list = sorted([str(x) for x in base_df['ภาค'].dropna().unique() if x])
    
    df_zone_temp = base_df.copy()
    r_val = filters.get('ภาค')
    if r_val and r_val != 'ทั้งหมด':
        df_zone_temp = df_zone_temp[df_zone_temp['ภาค'].astype(str).str.strip() == str(r_val).strip()]
    zones_list = sorted([str(x) for x in df_zone_temp['เขตสุขภาพ'].dropna().unique() if x], key=natural_keys)
    
    df_prov_temp = df_zone_temp.copy()
    z_val = filters.get('เขตสุขภาพ')
    if z_val and z_val != 'ทั้งหมด':
        df_prov_temp = df_prov_temp[df_prov_temp['เขตสุขภาพ'].astype(str).str.strip() == str(z_val).strip()]
    provinces_list = sorted([str(x) for x in df_prov_temp['จังหวัด'].dropna().unique() if x])
    
    df_dist_temp = df_prov_temp.copy()
    p_val = filters.get('จังหวัด')
    if p_val and p_val != 'ทั้งหมด':
        df_dist_temp = df_dist_temp[df_dist_temp['จังหวัด'].astype(str).str.strip() == str(p_val).strip()]
    districts_list = sorted([str(x) for x in df_dist_temp['อำเภอ'].dropna().unique() if x])
    
    df_subdist_temp = df_dist_temp.copy()
    d_val = filters.get('อำเภอ')
    if d_val and d_val != 'ทั้งหมด':
        df_subdist_temp = df_subdist_temp[df_subdist_temp['อำเภอ'].astype(str).str.strip() == str(d_val).strip()]
    subdistricts_list = sorted([str(x) for x in df_subdist_temp['ตำบล'].dropna().unique() if x])
    
    dropdowns = { 
        'years': ['ทั้งหมด'] + years_list, 
        'regions': ['ทั้งหมด'] + regions_list, 
        'zones': ['ทั้งหมด'] + zones_list, 
        'provinces': ['ทั้งหมด'] + provinces_list, 
        'districts': ['ทั้งหมด'] + districts_list, 
        'subdistricts': ['ทั้งหมด'] + subdistricts_list 
    }
 
    # Optimize column size by projecting only what frontend maps and charts need
    schema_keys = []
    try:
        with engine.connect() as conn:
            res = conn.execute(text("SELECT schema_data FROM report_schemas WHERE report_name = :n"), {"n": req_type}).fetchone()
            if res:
                schema_dict = json.loads(res[0]) if isinstance(res[0], str) else res[0]
                if isinstance(schema_dict, list):
                    schema_keys = schema_dict
                else:
                    schema_keys = schema_dict.get('fields', [])
    except Exception as e:
        print(f"Error loading schema keys in get_data: {e}")
    needed_cols = ['ปี', 'ภาค', 'เขตสุขภาพ', 'จังหวัด', 'อำเภอ', 'ตำบล', 'ละติจูด', 'ลองจิจูด', 'สถานการณ์']
    if is_dental:
        needed_cols += ['ชื่อหน่วยบริการ', 'พบฟันตกกระ', 'จำนวนตรวจ', 'severe_cases', 'ร้อยละเด็กฟันตกกระ']
    else:
        needed_cols += ['สถานที่เก็บ', 'ชนิดน้ำ', 'ปริมาณฟลูออไรด์']
        
    for col in schema_keys:
        if isinstance(col, dict) and col.get('name'):
            needed_cols.append(col.get('name'))
            
    cols_to_keep = list(set([c for c in needed_cols if c in df_filtered.columns]))
    df_projected = df_filtered[cols_to_keep]
 
    return jsonify({'dropdowns': dropdowns, 'table_data': df_projected.fillna("").to_dict('records')})

@app.route('/api/download_template/<cat>')
def download_template(cat):
    if cat == 'health':
        cols = ['รหัสหน่วยบริการ', 'ชื่อหน่วยบริการ', 'ปีงบประมาณ', 'ภาค', 'เขตสุขภาพ', 'จังหวัด', 'อำเภอ', 'ตำบล', 'ละติจูด', 'ลองจิจูด', 'จำนวนเด็กทั้งหมด', 'จำนวนตรวจ', 'พบฟันตกกระ', 'สถานการณ์']
    else:
        cols = ['ลำดับ', 'ชนิดน้ำ', 'สถานที่เก็บ', 'ปริมาณฟลูออไรด์', 'ว/ด/ป ที่เก็บ', 'บ้านเลขที่', 'หมู่ที่', 'ตำบล', 'อำเภอ', 'จังหวัด', 'เขตสุขภาพ', 'ภาค', 'ละติจูด', 'ลองจิจูด', 'หมายเหตุ', 'แหล่งข้อมูล']
    
    df = pd.DataFrame(columns=cols)
    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
    except ModuleNotFoundError:
        error_html = """
        <!DOCTYPE html>
        <html><head><meta charset="utf-8"><title>System Requirement Missing</title></head>
        <body style="font-family:sans-serif; text-align:center; padding-top:50px; background:#f8fafc;">
            <div style="background:white; max-width:600px; margin:0 auto; padding:30px; border-radius:12px; box-shadow:0 4px 6px rgba(0,0,0,0.1);">
                <h2 style="color:#ef4444;">⚠️ ระบบขาดไลบรารีสำหรับการจัดการไฟล์ Excel</h2>
                <p style="color:#475569; margin-bottom:20px;">กรุณาเปิดหน้าจอ Terminal หรือ Command Prompt ในเครื่องเซิร์ฟเวอร์ <br>แล้วพิมพ์คำสั่งด้านล่างนี้เพื่อติดตั้งไลบรารีที่จำเป็น:</p>
                <code style="background:#e2e8f0; padding:12px 24px; border-radius:8px; font-size:18px; color:#0f172a; display:inline-block; font-weight:bold;">pip install openpyxl</code>
                <br><br>
                <button onclick="window.history.back()" style="margin-top:20px; padding:10px 20px; background:#0ea5e9; color:white; border:none; border-radius:8px; cursor:pointer;">ย้อนกลับ</button>
            </div>
        </body></html>
        """
        return error_html, 500
    
    output.seek(0)
    return send_file(output, as_attachment=True, download_name=f"template_{cat}_{datetime.now().strftime('%Y%m%d')}.xlsx")

@app.route('/api/upload_data', methods=['POST'])
@require_admin
def upload_data():
    if 'file' not in request.files: return jsonify({'success': False, 'message': 'No file'})
    file = request.files['file']
    cat = request.form.get('category', 'health')
    table = 'dental_records' if cat == 'health' else 'water_records'
    
    try:
        df = pd.read_excel(file)
        
        if 'ลำดับ' in df.columns:
            df = df.drop(columns=['ลำดับ'])
            
        df.rename(columns=COLUMN_MAP_REV, inplace=True)
        
        if 'health_zone' not in df.columns: df['health_zone'] = 'ไม่ระบุ'
        if 'region' not in df.columns: df['region'] = 'ไม่ระบุ'
        if 'status' not in df.columns: df['status'] = 'ไม่ระบุ'
        if 'remark' not in df.columns: df['remark'] = '-'
        if 'data_source' not in df.columns: df['data_source'] = 'อัปโหลด'

        if cat == 'health':
            if 'fiscal_year' not in df.columns: df['fiscal_year'] = str(datetime.now().year + 543)
            if 'check_date' not in df.columns: df['check_date'] = df['fiscal_year'].astype(str) + "-01-01"
        
        required = ['fiscal_year', 'hospcode'] if cat == 'health' else ['check_date', 'location_name']
        for r in required:
            if r not in df.columns: return jsonify({'success': False, 'message': f'ขาดคอลัมน์สำคัญ: {r} หรือคุณยังใช้ฟอร์มเวอร์ชันเก่า'})
        
        if 'check_date' in df.columns:
            df['check_date'] = pd.to_datetime(df['check_date'], errors='coerce').dt.strftime('%Y-%m-%d')
        if 'fiscal_year' in df.columns:
            df['fiscal_year'] = df['fiscal_year'].astype(str)

        import_results = []
        
        with engine.connect() as conn:
            for idx, row in df.iterrows():
                row_dict = {k: v for k, v in row.dropna().to_dict().items() if k in VALID_DB_COLUMNS}
                
                if cat == 'health' and 'hospcode' in row_dict:
                    # Clean and pad hospcode to 5 characters
                    hc = str(row_dict['hospcode']).strip()
                    if '.' in hc: hc = hc.split('.')[0]
                    hc = hc.zfill(5)
                    row_dict['hospcode'] = hc
                    
                    try:
                        # Look up facility details from master table
                        facility = conn.execute(text("""
                            SELECT hosp_name, health_zone, province, district, subdistrict 
                            FROM health_facilities_master 
                            WHERE hospcode = :hc
                        """), {"hc": hc}).fetchone()
                        conn.commit()
                    except Exception as e:
                        conn.rollback()
                        facility = None
                    
                    if facility:
                        if not row_dict.get('hosp_name') or str(row_dict['hosp_name']).strip() == '':
                            row_dict['hosp_name'] = facility[0]
                        if not row_dict.get('health_zone') or str(row_dict['health_zone']).strip() == '' or row_dict['health_zone'] == 'ไม่ระบุ':
                            row_dict['health_zone'] = facility[1] or 'ไม่ระบุ'
                        if not row_dict.get('province') or str(row_dict['province']).strip() == '' or row_dict['province'] == 'ไม่ระบุ':
                            row_dict['province'] = facility[2] or 'ไม่ระบุ'
                        if not row_dict.get('district') or str(row_dict['district']).strip() == '' or row_dict['district'] == 'ไม่ระบุ':
                            row_dict['district'] = facility[3] or 'ไม่ระบุ'
                        if not row_dict.get('subdistrict') or str(row_dict['subdistrict']).strip() == '' or row_dict['subdistrict'] == 'ไม่ระบุ':
                            row_dict['subdistrict'] = facility[4] or 'ไม่ระบุ'
                        if not row_dict.get('region') or str(row_dict['region']).strip() == '' or row_dict['region'] == 'ไม่ระบุ':
                            row_dict['region'] = get_region_by_province(row_dict['province'])
                    else:
                        import_results.append({
                            'index': idx + 1,
                            'reference': f"รหัส {hc}",
                            'status': 'error',
                            'remark': f"ไม่พบรหัสหน่วยบริการ [{hc}] ในทะเบียนหน่วยบริการกลางของประเทศ"
                        })
                        continue
                
                ref_name = row_dict.get('hosp_name' if cat == 'health' else 'location_name', f"แถวที่ {idx+1}")
                
                if cat != 'health' and 'water_type' in row_dict:
                    wt = str(row_dict['water_type']).strip()
                    if any(k in wt for k in ['ภูเขา', 'บาดาล', 'บ่อ', 'แม่น้ำ', 'น้ำฝน', 'ดิบ']):
                        row_dict['water_category'] = 'แหล่งน้ำดิบ'
                    elif any(k in wt for k in ['ถัง', 'ขวด', 'หยอดเหรียญ', 'โรงเรียน', 'บริโภค']):
                        row_dict['water_category'] = 'แหล่งน้ำบริโภค'
                    elif any(k in wt for k in ['ประปาตำบล', 'ส่วนภูมิภาค', 'นครหลวง', 'ประปา']):
                        row_dict['water_category'] = 'แหล่งน้ำประปา'
                    else:
                        row_dict['water_category'] = 'ไม่ระบุ'
                
                if len(row_dict) > 0:
                    # Validate
                    row_errors = validate_row_data(row_dict, cat)
                    if row_errors:
                        import_results.append({
                            'index': idx + 1,
                            'reference': ref_name,
                            'status': 'error',
                            'remark': " | ".join(row_errors)
                        })
                        continue
                        
                    try:
                        place_holders_keys = list(row_dict.keys())
                        placeholders = ", ".join([f":{k}" for k in place_holders_keys])
                        cols = ", ".join([f"`{k}`" for k in place_holders_keys])
                        updates = ", ".join([f"`{k}`=VALUES(`{k}`)" for k in place_holders_keys])
                        sql = text(f"INSERT INTO {table} ({cols}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {updates}")
                        
                        result = conn.execute(sql, row_dict)
                        conn.commit()
                        
                        if result.rowcount == 1:
                            status, remark = 'new', 'เพิ่มข้อมูลใหม่'
                        elif result.rowcount in (0, 2):
                            status, remark = 'updated', 'อัปเดตข้อมูลเดิม'
                        else:
                            status, remark = 'updated', 'แก้ไขข้อมูล'
                            
                        import_results.append({'index': idx + 1, 'reference': ref_name, 'status': status, 'remark': remark})
                    except Exception as e:
                        conn.rollback()
                        import_results.append({'index': idx + 1, 'reference': ref_name, 'status': 'error', 'remark': str(e)})
        
        summary = { 'total': len(df), 'new': sum(1 for x in import_results if x['status'] == 'new'), 'updated': sum(1 for x in import_results if x['status'] == 'updated'), 'error': sum(1 for x in import_results if x['status'] == 'error') }
        
        username_operator = get_admin_username()
        log_audit(username_operator, 'UPLOAD_DATA', table, f"นำเข้าข้อมูลสถิติ {summary['total']} รายการ (เพิ่มใหม่ {summary['new']}, อัปเดต {summary['updated']}, ข้อผิดพลาด {summary['error']})")
        
        return jsonify({'success': True, 'summary': summary, 'details': import_results})
    except Exception as e: return jsonify({'success': False, 'message': str(e)})

@app.route('/api/save_schema', methods=['POST'])
@require_admin
def save_schema():
    data = request.json
    try:
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO report_schemas (report_name, category, schema_data) VALUES (:rn, :cat, :sd) ON DUPLICATE KEY UPDATE category=VALUES(category), schema_data=VALUES(schema_data)"), {"rn": data['report_name'], "cat": data['category'], "sd": json.dumps(data['schema_data'], ensure_ascii=False)})
        
        username_operator = get_admin_username()
        log_audit(username_operator, 'SAVE_SCHEMA', data['report_name'], f"Category: {data['category']}")
        
        return jsonify({'success': True})
    except Exception as e: return jsonify({'success': False, 'message': str(e)})

@app.route('/api/get_schemas', methods=['GET'])
def get_schemas():
    try:
        df = pd.read_sql("SELECT report_name, category, schema_data FROM report_schemas ORDER BY category, report_name", engine)
        schemas = {}
        for _, row in df.iterrows():
            raw = json.loads(row['schema_data']) if isinstance(row['schema_data'], str) else row['schema_data']
            if isinstance(raw, list):
                schemas[row['report_name']] = {'category': row['category'], 'fields': raw, 'config': {'proportion':'', 'proportion_rules': [], 'drilldown':'', 'map':'', 'kpis':[]}}
            else:
                schemas[row['report_name']] = {'category': row['category'], 'fields': raw.get('fields', []), 'config': raw.get('config', {})}
        return jsonify({'success': True, 'data': schemas})
    except: return jsonify({'success': False})

@app.route('/api/delete_schema', methods=['POST'])
@require_admin
def delete_schema():
    data = request.json
    try:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM report_schemas WHERE report_name = :rn"), {"rn": data['report_name']})
            
        username_operator = get_admin_username()
        log_audit(username_operator, 'DELETE_SCHEMA', data['report_name'], 'ลบโครงสร้างรายงานสำเร็จ')
        
        return jsonify({'success': True})
    except Exception as e: return jsonify({'success': False, 'message': str(e)})

@app.route('/api/table_data', methods=['POST'])
def get_table_data():
    req = request.json
    draw = int(req.get('draw', 1))
    start = int(req.get('start', 0))
    length = int(req.get('length', 10))
    search_val = req.get('search_value', '').strip()
    order_col = req.get('order_column', '')
    order_dir = req.get('order_direction', 'asc').lower()
    if order_dir not in ['asc', 'desc']: order_dir = 'asc'
    
    req_type = req.get('type', 'ทั้งหมด')
    is_dental = (get_cat(req_type) == 'health')
    table = 'dental_records' if is_dental else 'water_records'
    
    schema_keys = []
    if req_type and req_type != 'ทั้งหมด':
        try:
            with engine.connect() as conn:
                res = conn.execute(text("SELECT schema_data FROM report_schemas WHERE report_name = :n"), {"n": req_type}).fetchone()
                if res:
                    schema_keys = json.loads(res[0]) if isinstance(res[0], str) else res[0]
        except Exception as e:
            print(f"⚠️ Error loading schema for table_data: {e}")
            
    sql_base = f"SELECT * FROM {table} WHERE 1=1"
    params = {}
    
    if not is_dental and req_type != 'ทั้งหมด':
        search_term = req_type.replace('คุณภาพ', '').strip()
        sql_base += " AND water_type LIKE :water_type_filter"
        params['water_type_filter'] = f"%{search_term}%"
        
    filter_keys = {
        'ปี': 'fiscal_year' if is_dental else 'YEAR(STR_TO_DATE(check_date, "%Y-%m-%d"))',
        'ภาค': 'region',
        'เขตสุขภาพ': 'health_zone',
        'จังหวัด': 'province',
        'อำเภอ': 'district',
        'ตำบล': 'subdistrict'
    }
    
    for key, col in filter_keys.items():
        val = req.get(key)
        if val and val != 'ทั้งหมด':
            if key == 'ปี' and not is_dental:
                sql_base += " AND check_date LIKE :year_filter"
                params['year_filter'] = f"{val}%"
            else:
                sql_base += f" AND `{col}` = :{col}"
                params[col] = val.strip()
                
    if search_val:
        search_like = f"%{search_val}%"
        if is_dental:
            search_cols = ['hospcode', 'hosp_name', 'province', 'district', 'subdistrict', 'status']
        else:
            search_cols = ['location_name', 'water_type', 'province', 'district', 'subdistrict', 'status', 'remark', 'data_source']
            
        or_conds = " OR ".join([f"`{c}` LIKE :search_query" for c in search_cols])
        sql_base += f" AND ({or_conds})"
        params['search_query'] = search_like
        
    sql_count = f"SELECT COUNT(*) FROM ({sql_base}) AS count_tbl"
    try:
        with engine.connect() as conn:
            records_filtered = conn.execute(text(sql_count), params).fetchone()[0]
            records_total = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()[0]
            
            if order_col:
                col_map = {
                    'ร้อยละตกกระ (%)': 'pct_fluorosis',
                    'พบฟันตกกระ': 'fluorosis_cases',
                    'จำนวนตรวจ': 'screened_kids',
                    'ปริมาณฟลูออไรด์': 'fluoride_level',
                    'สถานการณ์': 'status'
                }
                db_sort_col = col_map.get(order_col, order_col)
                if db_sort_col in VALID_DB_COLUMNS or db_sort_col in col_map.values():
                    sql_base += f" ORDER BY `{db_sort_col}` {order_dir.upper()}"
            else:
                if is_dental:
                    sql_base += " ORDER BY `fiscal_year` DESC, `province` ASC, `district` ASC"
                else:
                    sql_base += " ORDER BY `check_date` DESC, `province` ASC, `district` ASC"
                    
            sql_base += " LIMIT :limit OFFSET :offset"
            params['limit'] = length
            params['offset'] = start
            
            rows = conn.execute(text(sql_base), params).fetchall()
            raw_data = [dict(r._mapping) for r in rows]
            processed_data = []
            
            if raw_data:
                df_raw = pd.DataFrame(raw_data)
                df_processed = pd.DataFrame(index=df_raw.index)
                if is_dental:
                    df_processed['ปีงบประมาณ'] = safe_extract(df_raw, 'fiscal_year', 'ไม่ระบุ')
                    df_processed['ปี'] = df_processed['ปีงบประมาณ']
                    df_processed['ภาค'] = safe_extract(df_raw, 'region', 'ไม่ระบุ')
                    df_processed['เขตสุขภาพ'] = safe_extract(df_raw, 'health_zone', 'ไม่ระบุ')
                    df_processed['จังหวัด'] = safe_extract(df_raw, 'province', 'ไม่ระบุ')
                    df_processed['อำเภอ'] = safe_extract(df_raw, 'district', 'ไม่ระบุ')
                    df_processed['ตำบล'] = safe_extract(df_raw, 'subdistrict', 'ไม่ระบุ')
                    df_processed['รหัสหน่วยบริการ'] = safe_extract(df_raw, 'hospcode', 'ไม่ระบุ')
                    df_processed['ชื่อหน่วยบริการ'] = safe_extract(df_raw, 'hosp_name', 'ไม่ระบุ')
                    df_processed['จำนวนเด็กทั้งหมด'] = pd.to_numeric(safe_extract(df_raw, 'total_kids', 0)).fillna(0)
                    df_processed['จำนวนตรวจ'] = pd.to_numeric(safe_extract(df_raw, 'screened_kids', 0)).fillna(0)
                    df_processed['พบฟันตกกระ'] = pd.to_numeric(safe_extract(df_raw, 'fluorosis_cases', 0)).fillna(0)
                    df_processed['ร้อยละเด็กฟันตกกระ'] = pd.to_numeric(safe_extract(df_raw, 'pct_fluorosis', 0.0)).fillna(0)
                    df_processed['severe_cases'] = pd.to_numeric(safe_extract(df_raw, 'severe_cases', 0)).fillna(0)
                    s_col = df_raw['dean_index_status'] if 'dean_index_status' in df_raw.columns else df_raw.get('status', pd.Series(['ปกติ (Normal)']*len(df_raw)))
                    dean_map = {'Normal': 'ปกติ (Normal)', 'Very Mild': 'ระดับอ่อนมาก (Very Mild)', 'Mild': 'ระดับอ่อน (Mild)', 'Moderate': 'ระดับปานกลาง (Moderate)', 'Severe': 'ระดับรุนแรง (Severe)'}
                    df_processed['สถานการณ์'] = s_col.replace(dean_map)
                    df_processed['ประเภทแหล่งน้ำ'] = 'สภาวะฟันตกกระ (เด็ก)'
                    df_processed['ละติจูด'] = pd.to_numeric(safe_extract(df_raw, 'latitude', 0.0)).fillna(0.0)
                    df_processed['ลองจิจูด'] = pd.to_numeric(safe_extract(df_raw, 'longitude', 0.0)).fillna(0.0)
                else:
                    dates = pd.to_datetime(df_raw['check_date'], errors='coerce')
                    df_processed['วันที่ตรวจ'] = dates.dt.strftime('%Y-%m-%d').fillna('')
                    df_processed['ว/ด/ป ที่เก็บ'] = df_processed['วันที่ตรวจ']
                    df_processed['ปี'] = dates.dt.strftime('%Y').fillna('')
                    df_processed['ภาค'] = safe_extract(df_raw, 'region', 'ไม่ระบุ')
                    df_processed['เขตสุขภาพ'] = safe_extract(df_raw, 'health_zone', 'ไม่ระบุ')
                    df_processed['จังหวัด'] = safe_extract(df_raw, 'province', 'ไม่ระบุ')
                    df_processed['อำเภอ'] = safe_extract(df_raw, 'district', 'ไม่ระบุ')
                    df_processed['ตำบล'] = safe_extract(df_raw, 'subdistrict', 'ไม่ระบุ')
                    df_processed['สถานที่เก็บ'] = safe_extract(df_raw, 'location_name', 'ไม่ระบุ')
                    df_processed['ชนิดน้ำ'] = safe_extract(df_raw, 'water_type', 'ไม่ระบุ')
                    df_processed['ปริมาณฟลูออไรด์'] = pd.to_numeric(safe_extract(df_raw, 'fluoride_level', 0.0)).fillna(0.0)
                    df_processed['สถานการณ์'] = safe_extract(df_raw, 'status', 'ไม่ระบุ')
                    df_processed['ละติจูด'] = pd.to_numeric(safe_extract(df_raw, 'latitude', 0.0)).fillna(0.0)
                    df_processed['ลองจิจูด'] = pd.to_numeric(safe_extract(df_raw, 'longitude', 0.0)).fillna(0.0)
                    df_processed['บ้านเลขที่'] = safe_extract(df_raw, 'house_no', '-')
                    df_processed['หมู่ที่'] = safe_extract(df_raw, 'moo', '-')
                    df_processed['หมายเหตุ'] = safe_extract(df_raw, 'remark', '-')
                    df_processed['แหล่งข้อมูล'] = safe_extract(df_raw, 'data_source', '-')
                
                # Apply custom formulas from schema
                fields = schema_keys.get('fields', []) if isinstance(schema_keys, dict) else schema_keys
                for col in fields:
                    fieldName = col.get('name')
                    db_ref = col.get('db_ref')
                    col_type = col.get('type')
                    formula = col.get('formula')
                    if col_type == 'Formula' or db_ref == 'f':
                        try:
                            calcStr = formula
                            matches = re.findall(r'\[(.*?)\]', calcStr)
                            results = []
                            for idx_p, row_p in df_processed.iterrows():
                                row_calc = calcStr
                                for m in matches:
                                    dbKey = API_TO_DB_REF_MAP.get(m, m)
                                    val_p = row_p.get(dbKey, row_p.get(m, 0))
                                    row_calc = row_calc.replace(f"[{m}]", str(val_p))
                                r_val = eval(row_calc)
                                results.append(round(float(r_val), 2) if isFinite(r_val) else 0.0)
                            df_processed[fieldName] = results
                        except Exception as e:
                            df_processed[fieldName] = 0.0
                    else:
                        dbKey = API_TO_DB_REF_MAP.get(db_ref, db_ref)
                        if dbKey in df_processed.columns:
                            df_processed[fieldName] = df_processed[dbKey]
                        else:
                            df_processed[fieldName] = df_raw.get(db_ref, '-')
                            
                processed_data = df_processed.fillna("").to_dict('records')
                
            return jsonify({
                'draw': draw,
                'recordsTotal': records_total,
                'recordsFiltered': records_filtered,
                'data': processed_data
            })
    except Exception as e:
        print(f"❌ Server-side table data error: {e}")
        return jsonify({
            'draw': draw,
            'recordsTotal': 0,
            'recordsFiltered': 0,
            'data': [],
            'error': str(e)
        })

@app.route('/api/log_visit', methods=['POST'])
def log_visit_route():
    data = request.json
    page_name = data.get('page_name', 'ไม่ระบุ')
    action_type = data.get('action_type', 'VIEW')
    log_visit(page_name, action_type)
    return jsonify({'success': True})

@app.route('/api/get_stats', methods=['GET'])
@require_admin
def get_stats():
    try:
        with engine.connect() as conn:
            # 1. Access Stats
            visits = conn.execute(text("SELECT page_name, COUNT(*) as count FROM user_visits GROUP BY page_name ORDER BY count DESC")).fetchall()
            visits_data = [{'page_name': r[0], 'count': r[1]} for r in visits]
            
            # 2. ROPA Logs
            audit = conn.execute(text("SELECT timestamp, username, action, target, details, ip_address FROM audit_logs ORDER BY timestamp DESC LIMIT 100")).fetchall()
            audit_data = [{
                'timestamp': r[0].strftime('%Y-%m-%d %H:%M:%S') if r[0] else '',
                'username': r[1],
                'action': r[2],
                'target': r[3],
                'details': r[4] or '',
                'ip_address': r[5] or ''
            } for r in audit]
            
            # 3. Admin Users
            admins = conn.execute(text("SELECT username, role, created_at FROM admin_users ORDER BY username ASC")).fetchall()
            admins_data = [{
                'username': r[0],
                'role': r[1],
                'created_at': r[2].strftime('%Y-%m-%d %H:%M:%S') if r[2] else ''
            } for r in admins]
            
            return jsonify({
                'success': True,
                'visits': visits_data,
                'audit': audit_data,
                'admins': admins_data
            })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/manage_admin', methods=['POST'])
@require_admin
def manage_admin():
    data = request.json
    action = data.get('action')
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not username:
        return jsonify({'success': False, 'message': 'ชื่อผู้ใช้งานห้ามว่าง'})
        
    username_operator = get_admin_username()
    
    try:
        with engine.begin() as conn:
            if action == 'add':
                if not password:
                    return jsonify({'success': False, 'message': 'รหัสผ่านห้ามว่าง'})
                p_hash = hashlib.sha256(password.encode()).hexdigest()
                conn.execute(text("INSERT INTO `admin_users` (`username`, `password_hash`, `role`) VALUES (:u, :ph, 'admin') ON DUPLICATE KEY UPDATE `password_hash` = :ph"), {"u": username, "ph": p_hash})
                log_audit(username_operator, 'ADD_ADMIN', username, 'เพิ่มหรืออัปเดตบัญชีแอดมิน')
                return jsonify({'success': True, 'message': 'เพิ่ม/อัปเดตบัญชีแอดมินสำเร็จ'})
            elif action == 'delete':
                if username == 'admin':
                    return jsonify({'success': False, 'message': 'ไม่สามารถลบบัญชีผู้ใช้หลัก (admin) ได้'})
                conn.execute(text("DELETE FROM `admin_users` WHERE `username` = :u"), {"u": username})
                log_audit(username_operator, 'DELETE_ADMIN', username, 'ลบบัญชีแอดมิน')
                return jsonify({'success': True, 'message': 'ลบบัญชีแอดมินสำเร็จ'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

def calculate_lisa_numpy(x, lats, lngs, k=5):
    n = len(x)
    if n <= 1:
        return [{'local_i': 0.0, 'p_value': 1.0, 'quadrant': 3, 'z_score': 0.0, 'z_lag': 0.0} for _ in range(n)], 0.0
    
    # Standardize x
    mean_x = np.mean(x)
    std_x = np.std(x)
    z = (x - mean_x) / std_x if std_x > 0 else np.zeros(n)
        
    # Standardize K
    k = min(k, max(1, n - 1))
    
    # Calculate distance matrix (using euclidean distance on Lat/Lng coordinates)
    coords = np.column_stack((lats, lngs))
    diff = coords[:, np.newaxis, :] - coords[np.newaxis, :, :]
    dist_matrix = np.sqrt(np.sum(diff**2, axis=-1))
    
    # Build weights matrix
    w = np.zeros((n, n))
    for i in range(n):
        nearest = np.argsort(dist_matrix[i])
        neighbors = nearest[1:k+1]
        w[i, neighbors] = 1.0
        
    # Row-standardize weights
    row_sums = w.sum(axis=1)
    row_sums[row_sums == 0] = 1.0
    w = w / row_sums[:, np.newaxis]
    
    # Spatial lag
    z_lag = np.dot(w, z)
    
    # Local Moran's I
    local_morans = z * z_lag
    
    # Permutation test for pseudo p-values
    num_permutations = 999
    simulated_local_morans = np.zeros((num_permutations, n))
    
    for p in range(num_permutations):
        perm_z = np.random.permutation(z)
        p_w = np.zeros((n, n))
        for i in range(n):
            pool = list(range(n))
            pool.remove(i)
            if len(pool) > 0:
                neighbors = np.random.choice(pool, k, replace=False)
                p_w[i, neighbors] = 1.0
        p_row_sums = p_w.sum(axis=1)
        p_row_sums[p_row_sums == 0] = 1.0
        p_w = p_w / p_row_sums[:, np.newaxis]
        
        sim_lag = np.dot(p_w, perm_z)
        simulated_local_morans[p] = z * sim_lag
        
    # pseudo p-value calculation
    p_values = np.zeros(n)
    for i in range(n):
        observed = local_morans[i]
        sim_vals = simulated_local_morans[:, i]
        if observed >= 0:
            larger = np.sum(sim_vals >= observed)
            p_values[i] = (larger + 1.0) / (num_permutations + 1.0)
        else:
            smaller = np.sum(sim_vals <= observed)
            p_values[i] = (smaller + 1.0) / (num_permutations + 1.0)
            
    # Classify quadrants:
    # 1: HH (z >= 0, z_lag >= 0)
    # 2: LH (z < 0, z_lag >= 0)
    # 3: LL (z < 0, z_lag < 0)
    # 4: HL (z >= 0, z_lag < 0)
    quadrants = np.zeros(n, dtype=int)
    for i in range(n):
        if z[i] >= 0 and z_lag[i] >= 0:
            quadrants[i] = 1
        elif z[i] < 0 and z_lag[i] >= 0:
            quadrants[i] = 2
        elif z[i] < 0 and z_lag[i] < 0:
            quadrants[i] = 3
        else:
            quadrants[i] = 4
            
    # Calculate Global Moran's I
    global_moran_i = float(np.mean(local_morans)) if n > 0 else 0.0
    
    lisa_results = []
    for i in range(n):
        lisa_results.append({
            'local_i': float(local_morans[i]),
            'p_value': float(p_values[i]),
            'quadrant': int(quadrants[i]),
            'z_score': float(z[i]),
            'z_lag': float(z_lag[i])
        })
        
    return lisa_results, global_moran_i

@app.route('/api/predict', methods=['POST'])
def predict_risk():
    try:
        filters = request.json or {}
        year_filter = filters.get('ปี')
        
        df_water, df_dental = load_data_from_db(load_water=True, load_dental=True)
        
        # Guard/fallback to full data if filtered data is empty or too small
        # Apply year filter first (which represents temporal change)
        if year_filter and year_filter != 'ทั้งหมด':
            df_w_filtered = df_water[df_water['ปี'].astype(str).str.strip() == str(year_filter).strip()]
            df_d_filtered = df_dental[df_dental['ปี'].astype(str).str.strip() == str(year_filter).strip()]
            if not df_w_filtered.empty and not df_d_filtered.empty:
                df_water, df_dental = df_w_filtered, df_d_filtered
        
        water_grouped = df_water.groupby(['จังหวัด', 'อำเภอ']).agg({
            'ปริมาณฟลูออไรด์': 'mean',
            'ภาค': 'first',
            'เขตสุขภาพ': 'first'
        }).reset_index()
        water_grouped.rename(columns={'ปริมาณฟลูออไรด์': 'water_avg_ppm'}, inplace=True)
        
        dental_grouped = df_dental.groupby(['จังหวัด', 'อำเภอ']).agg({
            'จำนวนตรวจ': 'sum',
            'พบฟันตกกระ': 'sum',
            'severe_cases': 'sum',
            'ละติจูด': 'mean',
            'ลองจิจูด': 'mean',
            'ภาค': 'first',
            'เขตสุขภาพ': 'first'
        }).reset_index()
        
        merged = pd.merge(water_grouped, dental_grouped, on=['จังหวัด', 'อำเภอ', 'ภาค', 'เขตสุขภาพ'], how='inner')
        
        if len(merged) < 3:
            # Fallback to outer join if inner join yields too few rows
            merged = pd.merge(water_grouped, dental_grouped, on=['จังหวัด', 'อำเภอ'], how='outer')
            
            # Resolve duplicate columns due to outer join without common keys in on=
            if 'ภาค_x' in merged.columns and 'ภาค_y' in merged.columns:
                merged['ภาค'] = merged['ภาค_x'].fillna(merged['ภาค_y']).fillna('ไม่ระบุ')
                merged.drop(columns=['ภาค_x', 'ภาค_y'], inplace=True)
            elif 'ภาค' not in merged.columns:
                merged['ภาค'] = 'ไม่ระบุ'
                
            if 'เขตสุขภาพ_x' in merged.columns and 'เขตสุขภาพ_y' in merged.columns:
                merged['เขตสุขภาพ'] = merged['เขตสุขภาพ_x'].fillna(merged['เขตสุขภาพ_y']).fillna('ไม่ระบุ')
                merged.drop(columns=['เขตสุขภาพ_x', 'เขตสุขภาพ_y'], inplace=True)
            elif 'เขตสุขภาพ' not in merged.columns:
                merged['เขตสุขภาพ'] = 'ไม่ระบุ'
                
            merged['ละติจูด'] = merged['ละติจูด'].fillna(13.0)
            merged['ลองจิจูด'] = merged['ลองจิจูด'].fillna(101.5)
            merged['จำนวนตรวจ'] = merged['จำนวนตรวจ'].fillna(100.0)
            merged['พบฟันตกกระ'] = merged['พบฟันตกกระ'].fillna(0.0)
            merged['severe_cases'] = merged['severe_cases'].fillna(0.0)
            merged['water_avg_ppm'] = merged['water_avg_ppm'].fillna(0.3)
            
        merged['fluorosis_rate'] = (merged['พบฟันตกกระ'] / merged['จำนวนตรวจ'].replace(0, np.nan) * 100).fillna(0.0)
        merged['severe_ratio'] = (merged['severe_cases'] / merged['จำนวนตรวจ'].replace(0, np.nan)).fillna(0.0)
        
        N = len(merged)
        X = np.ones((N, 3))
        X[:, 1] = merged['water_avg_ppm'].values
        X[:, 2] = merged['severe_ratio'].values
        y = merged['fluorosis_rate'].values
        
        try:
            XT = X.T
            XTX = np.dot(XT, X)
            XTX += np.eye(3) * 1e-4
            XTX_inv = np.linalg.inv(XTX)
            XTy = np.dot(XT, y)
            theta = np.dot(XTX_inv, XTy)
        except Exception as e:
            theta = np.array([1.5, 12.5, 8.0])
            
        alpha, beta, gamma = float(theta[0]), float(theta[1]), float(theta[2])
        
        predictions = []
        for idx, row in merged.iterrows():
            ppm = float(row['water_avg_ppm'])
            sev_ratio = float(row['severe_ratio'])
            pred_val = alpha + beta * ppm + gamma * sev_ratio
            pred_val = max(0.0, min(100.0, pred_val))
            
            if pred_val > 15.0:
                risk = 'วิกฤต (High Risk)'
            elif pred_val > 5.0:
                risk = 'เฝ้าระวัง (Medium Risk)'
            else:
                risk = 'ปกติ (Low Risk)'
                
            predictions.append({
                'province': str(row['จังหวัด']),
                'district': str(row['อำเภอ']),
                'region': str(row['ภาค']),
                'health_zone': str(row['เขตสุขภาพ']),
                'water_avg_ppm': round(ppm, 3),
                'fluorosis_cases': int(row['พบฟันตกกระ']),
                'severe_cases': int(row['severe_cases']),
                'predicted_risk_index': round(pred_val, 2),
                'risk_level': risk,
                'lat': float(row['ละติจูด']),
                'lng': float(row['ลองจิจูด'])
            })
            
        # Calculate Moran's LISA on predictions using numpy
        if len(predictions) > 0:
            x_vals = np.array([p['predicted_risk_index'] for p in predictions])
            lat_vals = np.array([p['lat'] for p in predictions])
            lng_vals = np.array([p['lng'] for p in predictions])
            
            lisa_results, global_moran_i = calculate_lisa_numpy(x_vals, lat_vals, lng_vals, k=5)
            
            for i, res in enumerate(lisa_results):
                predictions[i].update({
                    'lisa_i': round(res['local_i'], 4),
                    'lisa_p': round(res['p_value'], 4),
                    'lisa_quad': res['quadrant'],
                    'z_score': round(res['z_score'], 4),
                    'z_lag': round(res['z_lag'], 4)
                })
        else:
            global_moran_i = 0.0
            
        # Build cascading dropdown lists based on year-filtered predictions
        df_pred_all = pd.DataFrame(predictions)
        if not df_pred_all.empty:
            raw_w, raw_d = load_data_from_db(load_water=True, load_dental=True)
            years_list = sorted(list(set([str(x) for x in raw_w['ปี'].dropna().unique().tolist() + raw_d['ปี'].dropna().unique().tolist() if x])), reverse=True)
            regions_list = sorted(list(set([str(x) for x in df_pred_all['region'].dropna().unique() if x])))
            
            df_zone_temp = df_pred_all.copy()
            r_val = filters.get('ภาค')
            if r_val and r_val != 'ทั้งหมด':
                df_zone_temp = df_zone_temp[df_zone_temp['region'].astype(str).str.strip() == str(r_val).strip()]
            zones_list = sorted(list(set([str(x) for x in df_zone_temp['health_zone'].dropna().unique() if x])), key=natural_keys)
            
            df_prov_temp = df_zone_temp.copy()
            z_val = filters.get('เขตสุขภาพ')
            if z_val and z_val != 'ทั้งหมด':
                df_prov_temp = df_prov_temp[df_prov_temp['health_zone'].astype(str).str.strip() == str(z_val).strip()]
            provinces_list = sorted(list(set([str(x) for x in df_prov_temp['province'].dropna().unique() if x])))
            
            df_dist_temp = df_prov_temp.copy()
            p_val = filters.get('จังหวัด')
            if p_val and p_val != 'ทั้งหมด':
                df_dist_temp = df_dist_temp[df_dist_temp['province'].astype(str).str.strip() == str(p_val).strip()]
            districts_list = sorted(list(set([str(x) for x in df_dist_temp['district'].dropna().unique() if x])))
            
            dropdowns = {
                'years': ['ทั้งหมด'] + years_list,
                'regions': ['ทั้งหมด'] + regions_list,
                'zones': ['ทั้งหมด'] + zones_list,
                'provinces': ['ทั้งหมด'] + provinces_list,
                'districts': ['ทั้งหมด'] + districts_list,
                'subdistricts': ['ทั้งหมด']
            }
        else:
            dropdowns = {
                'years': ['ทั้งหมด'], 'regions': ['ทั้งหมด'], 'zones': ['ทั้งหมด'],
                'provinces': ['ทั้งหมด'], 'districts': ['ทั้งหมด'], 'subdistricts': ['ทั้งหมด']
            }
            
        # Apply filters (region, health_zone, province, district) to prediction results
        filtered_predictions = []
        for p in predictions:
            r_val = filters.get('ภาค')
            if r_val and r_val != 'ทั้งหมด' and p['region'] != r_val:
                continue
            z_val = filters.get('เขตสุขภาพ')
            if z_val and z_val != 'ทั้งหมด' and p['health_zone'] != z_val:
                continue
            p_val = filters.get('จังหวัด')
            if p_val and p_val != 'ทั้งหมด' and p['province'] != p_val:
                continue
            d_val = filters.get('อำเภอ')
            if d_val and d_val != 'ทั้งหมด' and p['district'] != d_val:
                continue
            filtered_predictions.append(p)
            
        filtered_predictions = sorted(filtered_predictions, key=lambda x: x['predicted_risk_index'], reverse=True)
        
        model_info = {
            'alpha': round(alpha, 4),
            'beta': round(beta, 4),
            'gamma': round(gamma, 4),
            'equation': f"อัตราฟันตกกระพยากรณ์ = {round(alpha, 2)} + {round(beta, 2)} * (ปริมาณฟลูออไรด์ ppm) + {round(gamma, 2)} * (สัดส่วนผู้ป่วยรุนแรง)",
            'global_moran_i': round(global_moran_i, 4)
        }
        
        return jsonify({
            'success': True,
            'predictions': filtered_predictions,
            'model': model_info,
            'dropdowns': dropdowns
        })
    except Exception as e:
        print(f"❌ AI Prediction error: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/investigation/submit', methods=['POST'])
def submit_investigation():
    data = request.json or {}
    hospcode = data.get('hospcode', '').strip()
    investigation_date = data.get('investigation_date', '').strip()
    severity_level = data.get('severity_level', '').strip()
    
    if not hospcode or not investigation_date or not severity_level:
        return jsonify({'success': False, 'message': 'กรุณากรอกข้อมูลที่จำเป็นให้ครบถ้วน (รหัสสถานบริการ, วันที่สอบสวนโรค, และระดับความรุนแรง)'}), 400
        
    try:
        # Lookup hosp_name from health_facilities_master
        hosp_name = "ไม่ระบุ"
        with engine.connect() as conn:
            facility = conn.execute(
                text("SELECT hosp_name FROM `health_facilities_master` WHERE hospcode = :h"),
                {"h": hospcode}
            ).fetchone()
            if facility:
                hosp_name = facility[0]
                
        # Insert into fluorosis_investigations
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO `fluorosis_investigations` 
                (hospcode, hosp_name, investigation_date, patient_gender, patient_age, severity_level, drinking_water_source, exposure_years, investigator_name, investigator_phone, details, status)
                VALUES (:hospcode, :hosp_name, :investigation_date, :patient_gender, :patient_age, :severity_level, :drinking_water_source, :exposure_years, :investigator_name, :investigator_phone, :details, 'Pending')
            """), {
                "hospcode": hospcode,
                "hosp_name": hosp_name,
                "investigation_date": investigation_date,
                "patient_gender": data.get('patient_gender', '-'),
                "patient_age": int(data.get('patient_age', 0) or 0),
                "severity_level": severity_level,
                "drinking_water_source": data.get('drinking_water_source', '-'),
                "exposure_years": int(data.get('exposure_years', 0) or 0),
                "investigator_name": data.get('investigator_name', '-'),
                "investigator_phone": data.get('investigator_phone', '-'),
                "details": data.get('details', '-'),
            })
            
        return jsonify({'success': True, 'message': 'ส่งรายงานสอบสวนโรคสำเร็จ!'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'เกิดข้อผิดพลาดในการบันทึกข้อมูล: {str(e)}'}), 500

@app.route('/api/investigation/list', methods=['POST'])
@require_admin
def list_investigations():
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT id, hospcode, hosp_name, investigation_date, patient_gender, patient_age, 
                       severity_level, drinking_water_source, exposure_years, investigator_name, 
                       investigator_phone, details, status, created_at 
                FROM `fluorosis_investigations`
                ORDER BY created_at DESC
            """)).fetchall()
            
        investigations = []
        for r in rows:
            investigations.append({
                'id': r[0],
                'hospcode': r[1],
                'hosp_name': r[2],
                'investigation_date': r[3],
                'patient_gender': r[4],
                'patient_age': r[5],
                'severity_level': r[6],
                'drinking_water_source': r[7],
                'exposure_years': r[8],
                'investigator_name': r[9],
                'investigator_phone': r[10],
                'details': r[11],
                'status': r[12],
                'created_at': r[13].strftime('%Y-%m-%d %H:%M:%S') if r[13] else '-'
            })
            
        return jsonify({'success': True, 'data': investigations})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)