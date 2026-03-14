import requests
import logging
from config import Config

# Set up logging
logger = logging.getLogger(__name__)

def offline_server_handler(func):
    def wrapper(self, *args, **kwargs):
        logger.info("="*50)
        logger.info("CALLING _get_response_json()")
        response_json = self._get_response_json()
        logger.info(f"Response from _get_response_json: {response_json}")
        
        # Check if the server is online
        if not response_json.get("online", False):
            error_msg = response_json.get("error", "Unknown error")
            logger.error(f"Server offline check triggered. Error: {error_msg}")
            if error_msg is None:
                error_msg = "No data received from any API"
            
            return {
                "status": "error",
                "message": f"⚠️ Server status: {error_msg}"
            }
        
        logger.info("Server is online, proceeding to function")
        return func(self, response_json, *args, **kwargs)
    return wrapper

class Minecraft_Status:
    def __init__(self):
        self.MINECRAFT_SERVER_ADDRESS = Config.MINECRAFT_SERVER_ADDRESS
        logger.info(f"Minecraft_Status initialized with address: {self.MINECRAFT_SERVER_ADDRESS}")
    
    def _get_response_json(self):
        logger.info("\n" + "="*60)
        logger.info("STARTING API CALLS")
        logger.info(f"Server address: {self.MINECRAFT_SERVER_ADDRESS}")
        
        # Split address for APIs that need separate IP and port
        if ':' in self.MINECRAFT_SERVER_ADDRESS:
            ip, port = self.MINECRAFT_SERVER_ADDRESS.split(':')
        else:
            ip = self.MINECRAFT_SERVER_ADDRESS
            port = '25565'
        
        logger.info(f"Split into IP: {ip}, Port: {port}")
        
        # List of APIs to try in order
        apis = [
            f"https://api.mcstatus.io/v2/status/java/{self.MINECRAFT_SERVER_ADDRESS}",
            f"https://api.mcsrvstat.us/2/{self.MINECRAFT_SERVER_ADDRESS}",
            f"https://mcapi.us/server/status?ip={ip}&port={port}",
            f"https://api.minetools.eu/ping/{ip}/{port}",
            # Add a simple test to see if we can reach anything
            f"https://api.mcsrvstat.us/2/mc.hypixel.net"
        ]
        
        # Try each API until one works
        for i, api_url in enumerate(apis):
            try:
                logger.info(f"\n--- TRYING API #{i+1} ---")
                logger.info(f"URL: {api_url}")
                
                # Make the request with a timeout
                response = requests.get(api_url, timeout=10)
                logger.info(f"Status code: {response.status_code}")
                logger.info(f"Response headers: {dict(response.headers)}")
                logger.info(f"First 200 chars of response: {response.text[:200]}")
                
                if response.status_code == 200:
                    try:
                        response_json = response.json()
                        logger.info(f"JSON parsed successfully. Keys: {list(response_json.keys())}")
                        
                        # Check if this is the test API (Hypixel)
                        if "mc.hypixel.net" in api_url:
                            logger.info(f"TEST API RESULT (Hypixel): online={response_json.get('online')}")
                            logger.info("✅ This proves the API itself works and Railway has internet!")
                            continue
                        
                        normalized_data = self._normalize_api_response(api_url, response_json)
                        
                        if normalized_data:
                            logger.info(f"Normalized data: {normalized_data}")
                            if normalized_data.get("online") is True:
                                logger.info(f"✅ SUCCESS! API #{i+1} works!")
                                return normalized_data
                            else:
                                logger.info(f"❌ API #{i+1} reports server offline: {normalized_data.get('error')}")
                        else:
                            logger.info(f"❌ API #{i+1} normalization failed")
                            
                    except Exception as json_err:
                        logger.error(f"JSON parse error: {str(json_err)}")
                else:
                    logger.info(f"❌ API #{i+1} returned non-200 status")
                    
            except requests.exceptions.Timeout:
                logger.error(f"❌ API #{i+1} timed out after 10 seconds")
            except requests.exceptions.ConnectionError as e:
                logger.error(f"❌ API #{i+1} connection error: {str(e)}")
            except Exception as e:
                logger.error(f"❌ API #{i+1} failed with error: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
        
        # If all APIs fail, return a standardized offline response
        logger.error("\n❌ ALL APIS FAILED - Returning offline status")
        logger.info("Performing final internet connectivity check...")
        try:
            test = requests.get("https://api.mcsrvstat.us/2/mc.hypixel.net", timeout=5)
            logger.info(f"Internet check status: {test.status_code}")
            if test.status_code == 200:
                logger.info("✅ Internet is working, APIs just don't like your server")
                logger.info(f"Test response: {test.text[:200]}")
            else:
                logger.error(f"❌ Internet check returned {test.status_code}")
        except Exception as e:
            logger.error(f"❌ Internet check FAILED: {str(e)}")
        
        return {
            "online": False,
            "players": {
                "online": 0,
                "max": 0,
                "list": []
            },
            "version": "Unknown",
            "error": f"Could not connect to any status API for {self.MINECRAFT_SERVER_ADDRESS}"
        }

    def _normalize_api_response(self, api_url, response_json):
        """
        Convert different API response formats to a standard format
        """
        try:
            normalized = {
                "online": False,
                "players": {
                    "online": 0,
                    "max": 0,
                    "list": []
                },
                "version": "Unknown",
                "error": None
            }
            
            # mcstatus.io format
            if "api.mcstatus.io" in api_url:
                logger.info("Normalizing mcstatus.io response")
                normalized["online"] = response_json.get("online", False)
                if normalized["online"]:
                    players = response_json.get("players", {})
                    normalized["players"]["online"] = players.get("online", 0)
                    normalized["players"]["max"] = players.get("max", 0)
                    normalized["players"]["list"] = [p.get("name") for p in players.get("list", [])]
                    normalized["version"] = response_json.get("version", {}).get("name", "Unknown")
            
            # mcsrvstat.us format
            elif "mcsrvstat.us" in api_url:
                logger.info("Normalizing mcsrvstat.us response")
                normalized["online"] = response_json.get("online", False)
                if normalized["online"]:
                    players = response_json.get("players", {})
                    normalized["players"]["online"] = players.get("online", 0)
                    normalized["players"]["max"] = players.get("max", 0)
                    normalized["players"]["list"] = players.get("list", [])
                    normalized["version"] = response_json.get("version", "Unknown")
            
            # mcapi.us format
            elif "mcapi.us" in api_url:
                logger.info("Normalizing mcapi.us response")
                normalized["online"] = response_json.get("status", False)
                if normalized["online"]:
                    players = response_json.get("players", {})
                    normalized["players"]["online"] = players.get("now", 0)
                    normalized["players"]["max"] = players.get("max", 0)
                    normalized["players"]["list"] = []
                    normalized["version"] = response_json.get("server", {}).get("name", "Unknown")
            
            # minetools.eu format
            elif "minetools.eu" in api_url:
                logger.info("Normalizing minetools.eu response")
                if "error" not in response_json:
                    normalized["online"] = True
                    normalized["players"]["online"] = response_json.get("players", {}).get("online", 0)
                    normalized["players"]["max"] = response_json.get("players", {}).get("max", 0)
                    
                    player_sample = response_json.get("players", {}).get("sample", [])
                    if player_sample and isinstance(player_sample, list):
                        normalized["players"]["list"] = [p.get("name") for p in player_sample if isinstance(p, dict)]
                    
                    normalized["version"] = response_json.get("version", {}).get("name", "Unknown")
                else:
                    normalized["error"] = response_json.get("error", "Server offline")
            
            logger.info(f"Normalization complete: online={normalized['online']}")
            return normalized
            
        except Exception as e:
            logger.error(f"Error normalizing API response: {str(e)}")
            return None

    @offline_server_handler
    def get_online_users_count(self, response_json):
        logger.info("get_online_users_count called")
        return {
            "status": "success",
            "online_users_count": response_json.get("players", {}).get("online", 0)
        }

    @offline_server_handler
    def get_online_users_names(self, response_json):
        logger.info("get_online_users_names called")
        player_list = response_json.get("players", {}).get("list", [])
        
        if not player_list:
            player_list = []
        
        logger.info(f"Player list: {player_list}")
        return {
            "status": "success",
            "online_users_names": player_list
        }
