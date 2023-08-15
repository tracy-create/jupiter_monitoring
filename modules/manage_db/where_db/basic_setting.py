from modules.manage_db.where_db import postgresDBModule
from datetime import datetime
from models import models

def get_place_info(db_conn: postgresDBModule.DBConnection) -> dict:
    place_info = get_sectors(db_conn)
    place_info = get_buildings(place_info, db_conn)
    place_info = get_levels(place_info, db_conn)
    return place_info

def get_sectors(db_conn) -> dict:
    place_info = {}
    SELECT_QUERY = """SELECT id, name FROM sectors
                    ORDER BY id"""
    conn = db_conn.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(SELECT_QUERY)
            tuple_sectors = cur.fetchall()
    except Exception as error:
        raise Exception (f"select parameter Error : {error}")
    finally:
        db_conn.put_db_connection(conn)

    for tuple_sector in tuple_sectors:
        place_info[tuple_sector[0]] = [tuple_sector[1]]

    return place_info

def get_buildings(place_info: dict, db_conn: postgresDBModule.DBConnection) -> dict:
    SELECT_QUERY = """SELECT b.sector_id, b.name FROM buildings AS b
                    INNER JOIN sectors AS s
                    ON s.id = b.sector_id
                    ORDER BY s.id"""
    
    conn = db_conn.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(SELECT_QUERY)
            buildings_order_by_sector_id = cur.fetchall()
    except Exception as error:
        raise Exception (f"select parameter Error : {error}")
    finally:
        db_conn.put_db_connection(conn)

    buildings = []
    prev_sector_id = 0
    for idx, tuple_building in enumerate(buildings_order_by_sector_id):
        if idx == 0:
            prev_sector_id = tuple_building[0]
            buildings.append(tuple_building[1])
            continue

        if tuple_building[0] == prev_sector_id:
            buildings.append(tuple_building[1])
        else:
            place_info[prev_sector_id].append(buildings)
            buildings = []
            buildings.append(tuple_building[1])

        prev_sector_id = tuple_building[0]

    return place_info

def get_levels(place_info: dict, db_conn: postgresDBModule.DBConnection) -> dict:
    SELECT_QUERY = """SELECT b.sector_id, b.id, l.short_name FROM levels AS l
                    INNER JOIN buildings AS b ON b.id = l.building_id
                    INNER JOIN sectors AS s ON s.id = b.sector_id
                    ORDER BY s.id, b.id"""
    
    conn = db_conn.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(SELECT_QUERY)
            levels_order_by_sector_id = cur.fetchall()
    except Exception as error:
        raise Exception (f"select parameter Error : {error}")
    finally:
        db_conn.put_db_connection(conn)

    levels = []
    prev_sector_id, prev_building_id = 0, 0
    for idx, tuple_level in enumerate(levels_order_by_sector_id):
        if idx == 0:
            prev_sector_id, prev_building_id = tuple_level[0], tuple_level[1]
            levels.append(tuple_level[2])
            continue

        if tuple_level[0] == prev_sector_id:
            if tuple_level[1] == prev_building_id:
                levels.append(tuple_level[2])
            else:
                levels.append("")
        else:
            place_info[prev_sector_id].append(levels)
            levels = []
            levels.append(tuple_level[2])

        prev_sector_id = tuple_level[0]
        prev_building_id = tuple_level[1]

    return place_info

def select_user_ids(db_conn: postgresDBModule.DBConnection, sector_id, start_time, end_time) -> list:
    SELECT_QUERY = """SELECT DISTINCT mr.user_id FROM mobile_results AS mr
            WHERE mr.sector_id = %s AND mr.mobile_time >= %s AND mr.mobile_time < %s"""
    
    conn = db_conn.get_db_connection()
    try:
        records = db_conn.executeAll(SELECT_QUERY, (sector_id, start_time, end_time, ))
    except Exception as error:
        raise Exception (f"error while selecting user ids and device models : {error}")
    finally:
        db_conn.put_db_connection(conn)

    user_ids = []

    for record in records:
        user_ids.append(record[0])

    return user_ids

def count_request_outputs(db_conn: postgresDBModule.DBConnection, user, start_time, end_time):
    SELECT_QUERY = """SELECT COUNT(*)
                    FROM request_outputs
                    WHERE user_id = %s
                    AND mobile_time >= %s AND mobile_time < %s
                    """
    conn = db_conn.get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(SELECT_QUERY, (user, start_time, end_time, ))
            total_count = cur.fetchone()[0]
    except Exception as error:
        raise Exception (f"error while counting datas : {error}")
    finally:
        db_conn.put_db_connection(conn)

    return total_count

# sector_id 연계해서 언젠간 작성해야 함
def get_whole_request_output_data(db_conn: postgresDBModule.DBConnection, user: str, start_time: datetime, end_time: datetime) -> models.OneuserWholeTestSets:
    SELECT_QUERY = """SELECT mobile_time, index, building_name
                    FROM request_outputs
                    WHERE mobile_time >= %s AND mobile_time < %s
                    AND user_id = %s
                    ORDER BY mobile_time
                    """
    conn = db_conn.get_db_connection()
    try:
        total_mobile_results = db_conn.executeAll(SELECT_QUERY, (start_time, end_time, user, ))
    except Exception as error:
        raise Exception (f"error while counting datas : {error}")
    finally:
        db_conn.put_db_connection(conn)

    if len(total_mobile_results) == 0:
        return  models.OneuserWholeTestSets()
    
    return divide_test_sets(total_mobile_results, user)

def divide_test_sets(total_mobile_results: list, user: str) -> models.OneuserWholeTestSets:
    test = models.TestSet()
    whole_testsets = models.OneuserWholeTestSets(
        user_id=user
    )
    first_time_set, next_test_set = False, False
    prev_db_idx: int = -1 

    for idx, data in enumerate(total_mobile_results):
        if first_time_set == False and data[2] != "":
            test.start_time = data[0]
            first_time_set = True
            prev_db_idx = data[1]
            continue

        if data[1] < prev_db_idx:
            test.end_time = total_mobile_results[idx-1][0]
            if test.start_time != test.end_time:
                whole_testsets.test_sets.append(test)
            test = models.TestSet(
                start_time=data[0]
            )
            next_test_set = True
        
        prev_db_idx = data[1]

        if idx == len(total_mobile_results)-1:
            if first_time_set or next_test_set:
                test.end_time = data[0]
                if test.start_time != test.end_time:
                    whole_testsets.test_sets.append(test)

    return whole_testsets
