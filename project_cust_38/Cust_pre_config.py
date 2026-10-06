import sys
import os

def reg_env_db_users(pathdb:str = "SRV:BD_users.db"):
    k_v = f'"BD_users": "{pathdb}"'
    os.environ['MODIFIED_CFG'] = '{'+ k_v +'}'