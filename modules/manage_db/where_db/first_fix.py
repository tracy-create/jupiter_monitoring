from datetime import datetime
from models import models
from modules.manage_db.where_db import postgresDBModule

def get_phase_one_to_four_time(db_conn: postgresDBModule.DBConnection, one_day_whole_test_sets: list, start_time: datetime, end_time: datetime, sector_id: int) -> models.TimeToFirstFix:
    trial_count, total_time = 0, 0

    for one_user in one_day_whole_test_sets:
        for one_test in one_user.test_sets:
            exists = check_phase_four_exists(db_conn, one_user.user_id, one_test.start_time, one_test.end_time)
            if not exists:
                continue

            phase_one_time = one_test.start_time
            phase_four_time = get_phase_four_time(db_conn, phase_one_time, end_time, one_user.user_id)
            ttff = (phase_four_time -  phase_one_time).seconds

            total_time += ttff
            trial_count += 1

    stabilization_info = models.TimeToFirstFix(
        sector_id=sector_id,
        calc_date=start_time,
        avg_stabilization_time=total_time/trial_count,
        user_count=trial_count
    )

    return stabilization_info

def get_phase_one_time(db_conn: postgresDBModule.DBConnection, user: str, start_time: datetime, end_time: datetime) -> datetime:
    SELECT_QUERY = """SELECT mobile_time FROM request_outputs
                    WHERE mobile_time >= %s
                    AND mobile_time < %s
                    AND user_id = %s
                    ORDER BY mobile_time
                    LIMIT 1"""
    
    conn = db_conn.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(SELECT_QUERY, (start_time, end_time, user, ))
            phase_one_time = cur.fetchone()[0]
    except Exception as error:
        raise Exception (f"error while reading tables: {error}")
    finally:
        db_conn.put_db_connection(conn)

    return phase_one_time


def check_phase_four_exists(db_conn: postgresDBModule.DBConnection, user: str, start_time: datetime, end_time: datetime) -> bool:

    EXISTS_QUERY = """SELECT EXISTS
                    (SELECT 1
                        FROM request_outputs
                        WHERE mobile_time >= %s
                        AND mobile_time < %s
                        AND user_id = %s
                        AND phase = 4
                    ) AS exists_flag"""
    
    conn = db_conn.get_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(EXISTS_QUERY, (start_time, end_time, user, ))
            exists = cur.fetchone()[0]

    except Exception as error:
        db_conn.put_db_connection(conn)
        raise 
    finally:
        db_conn.put_db_connection(conn)

    return exists

def get_phase_four_time(db_conn: postgresDBModule.DBConnection, phase_one_time: datetime, end_time: datetime, user: str) -> datetime:
    SELECT_QUERY = """SELECT mobile_time FROM request_outputs
                    WHERE mobile_time >= %s
                    AND mobile_time < %s
                    AND user_id = %s
                    AND phase = 4
                    ORDER BY mobile_time
                    LIMIT 1"""
    
    conn = db_conn.get_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(SELECT_QUERY, (phase_one_time, end_time, user, ))
            phase_four_time = cur.fetchone()[0]

    except Exception as error:
        raise Exception (f"error while reading tables: {error}")
    finally:
        db_conn.put_db_connection(conn)

    return phase_four_time