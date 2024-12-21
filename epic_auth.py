import aiohttp
import requests
import asyncio
import os
import platform
import json
import math
from datetime import datetime, timezone
from cosmetic import FortniteCosmetic
from utils import bool_to_emoji

# these tokens are used to authorize in epic games's API and let us do the skincheck without getting errors
EPIC_API_SWITCH_TOKEN = "OThmN2U0MmMyZTNhNGY4NmE3NGViNDNmYmI0MWVkMzk6MGEyNDQ5YTItMDAxYS00NTFlLWFmZWMtM2U4MTI5MDFjNGQ3"
# keep in mind, sometimes epic games block the client ids, so then you have to generate new ios token for it to start working again
EPIC_API_IOS_CLIENT_TOKEN = "M2Y2OWU1NmM3NjQ5NDkyYzhjYzI5ZjFhZjA4YThhMTI6YjUxZWU5Y2IxMjIzNGY1MGE2OWVmYTY3ZWY1MzgxMmU="

class EpicEndpoints:
    endpoint_oauth_token = "https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token"
    endpoint_prod03_oauth_token = "https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/token"
    endpoint_redirect_url = "https://www.epicgames.com/id/login?redirectUrl=https%3A//www.epicgames.com/id/login%3FredirectUrl%3Dhttps%253A%252F%252Fwww.epicgames.com%252Fid%252Fapi%252Fredirect%253FclientId%253Dec684b8c687f479fadea3cb2ad83f5c6%2526responseType%253Dcode"
    endpoint_oauth_exchange = "https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/exchange"
    endpoint_device_auth = "https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/deviceAuthorization"

class EpicUser:
    def __init__(self, data: dict = {}):
        self.raw = data

        # api response for login link generation
        self.access_token = data.get("access_token", "")
        self.expires_in = data.get("expires_in", 0)
        self.expires_at = data.get("expires_at", "")
        self.token_type = data.get("token_type", "")
        self.client_id = data.get("client_id", "")
        self.internal_client = data.get("internal_client", False)
        self.client_service = data.get("client_service", "")
        self.product_id = data.get("product_id", "")
        self.application_id = data.get("application_id", "")

        # api response for account metadata
        self.refresh_token = data.get("refresh_token", "")
        self.refresh_expires = data.get("refresh_expires", "")
        self.refresh_expires_at = data.get("refresh_expires_at", "")
        self.account_id = data.get("account_id", "")
        self.display_name = data.get("displayName", "")
        self.app = data.get("app", "")
        self.in_app_id = data.get("in_app_id", "")
        self.acr = data.get("acr", "")
        self.auth_time = data.get("auth_time", "")

class LockerData:
    def __init__(self):
        self.cosmetic_categories = {}
        self.cosmetic_array = {}
        self.unlocked_styles = {}
        self.homebase_banners = {}

    def to_dict(self):
        return {
            "cosmetic_categories": self.cosmetic_categories,
            "cosmetic_array": self.cosmetic_array,
            "unlocked_styles": self.unlocked_styles,
            "homebase_banners": self.homebase_banners,
        }
    
class EpicGenerator:
    def __init__(self) -> None:
        # init the generator
        self.http: aiohttp.ClientSession
        self.user_agent = f"DeviceAuthGenerator/{platform.system()}/{platform.version()}"
        self.access_token = ""

    async def start(self) -> None:
        self.http = aiohttp.ClientSession(headers={"User-Agent": self.user_agent})
        self.access_token = await self.get_access_token()

    async def kill(self) -> None:
        await self.http.close()
    
    async def get_access_token(self) -> str:
        # getting the access token from epic's api(REQUIRES usage of EPIC_API_SWITCH_TOKEN as Authorization in headers for it to work)
        # if it's not getting any data, it means the EPIC_API_SWITCH_TOKEN is expired, you must find new one :D
        async with self.http.request(
            method="POST",
            url=EpicEndpoints.endpoint_oauth_token,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"basic {EPIC_API_SWITCH_TOKEN}"
            },
            data={ "grant_type": "client_credentials" },
        ) as response:
            data = await response.json()
            return data["access_token"]
        
    async def create_device_code(self) -> tuple:
        # devide code is used on the link the checker bot sends u "active?userCode=SOMETHING" something like this
        # REQUIRES usage of self.access_token, which we got from get_access_token function, as Authorization in headers
        # returns the device code, used in the link we generate for the user to login
        async with self.http.request(
            method="POST",
            url=EpicEndpoints.endpoint_device_auth,
            headers={
                "Authorization": f"bearer {self.access_token}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
        ) as response:
            data = await response.json()
            return data
        
    async def create_exchange_code(self, user: EpicUser) -> str:
        # creates exchange code for the api requests & returns it
        # REQUIRES usage of user.access_token, which we got from get_access_token function, as Authorization in headers
        async with self.http.request(
            method="GET",
            url=EpicEndpoints.endpoint_oauth_exchange,
            headers={"Authorization": f"bearer {user.access_token}"},
        ) as response:
            data = await response.json()
            return data["code"]
    
    async def wait_for_device_code_completion(self, code: str) -> EpicUser:
        # REQUIRES usage of EPIC_API_SWITCH_TOKEN as Authorization in headers
        # the device code completion runs forever, until the code expires
        while True:
            async with self.http.request(
                method="POST",
                url=EpicEndpoints.endpoint_prod03_oauth_token,
                headers={
                    "Authorization": f"basic {EPIC_API_SWITCH_TOKEN}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"grant_type": "device_code", "device_code": code},
            ) as request:
                token_data = await request.json()
                if request.status == 200:
                    break
                else:
                    if (token_data["errorCode"] == "errors.com.epicgames.account.oauth.authorization_pending"):
                        pass
                    elif token_data["errorCode"] == "g":
                        pass

                await asyncio.sleep(10)

        async with self.http.request(
            method="GET",
            url=EpicEndpoints.endpoint_oauth_exchange,
            headers={"Authorization": f"bearer {token_data['access_token']}"},
        ) as request:
            exchange_data = await request.json()

        # REQUIRES usage of EPIC_API_IOS_CLIENT_TOKEN as Authorization in the headers
        # if it returns that the device is blocked, create a new iOS client token!
        async with self.http.request(
            method="POST",
            url=EpicEndpoints.endpoint_prod03_oauth_token,
            headers={
                "Authorization": f"basic {EPIC_API_IOS_CLIENT_TOKEN}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            data={
                "grant_type": "exchange_code",
                "exchange_code": exchange_data["code"]
            },
        ) as request:
            auth_data = await request.json()
            
            return EpicUser(data=auth_data)
        
    async def create_device_auths(self, user: EpicUser) -> dict:
        # creates device auth
        # REQUIRES usage of user.access_token as Authorization in headers
        async with self.http.request(
            method="POST",
            url=f"https://account-public-service-prod.ol.epicgames.com/account/api/public/account/{user.account_id}/deviceAuth",
            headers={
                "Authorization": f"bearer {user.access_token}",
                "Content-Type": "application/json",
            },
        ) as request:
            data = await request.json()

        return {
            "device_id": data["deviceId"],
            "account_id": data["accountId"],
            "secret": data["secret"],
            "user_agent": data["userAgent"],
            "created": {
                "location": data["created"]["location"],
                "ip_address": data["created"]["ipAddress"],
                "datetime": data["created"]["dateTime"],
            },
        }
    
    async def get_account_metadata(self, user: EpicUser) -> json:
        # grabs account's metadata(basic information) from the api
        # REQUIRES usage of user.access_token as Authorization in headers
        async with self.http.request(
            method="GET",
            url=f'https://account-public-service-prod03.ol.epicgames.com/account/api/public/account/displayName/{user.display_name}',
            headers={
                "Authorization": f"bearer {user.access_token}",
                "Content-Type": "application/json",
            }
        ) as request:
            metadata = await request.json()

        return metadata;

    async def get_external_connections(self, user: EpicUser) -> dict:
        # returns external connected accounts info
        # REQUIRES usage of user.access_token as Authorization in headers
        async with self.http.request(
            method="GET",
            url=f"https://account-public-service-prod03.ol.epicgames.com/account/api/public/account/{user.account_id}/externalAuths",
            headers={"Authorization": f"bearer {user.access_token}"}
        ) as resp:
            if resp.status != 200:
                return []
            
            external_auths = await resp.json()
            with open('dumps/external_auth.txt', 'w') as ext_file:
                json.dump(external_auths, ext_file, indent=4)

        return external_auths
        
    async def get_public_account_info(self, user: EpicUser) -> dict:
        # returns basic public info about the account
        # REQUIRES usage of user.access_token as Authorization in headers
        async with self.http.request(
            method="GET",
            url=f"https://account-public-service-prod03.ol.epicgames.com/account/api/public/account/{user.account_id}",
            headers={"Authorization": f"bearer {user.access_token}"}
        ) as resp:
            if resp.status != 200:
                return {"error": f"Error fetching account info ({resp.status})"}
            account_data = await resp.json() 

            account_info = {} # creating json for only stuff we are interested into
            creation_date = account_data.get("created", "?")
            if creation_date != "?":
                creation_date = datetime.strptime(creation_date, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%d/%m/%Y")

            account_info['creation_date'] = creation_date
            account_info['externalAuths'] = await self.get_external_connections(user)

        return account_info
    
    async def get_common_profile(self, user: EpicUser) -> json:
        # gets the common profile, containing vbucks, receipts amount, vbucks purchases history, banners list
        # REQUIRES usage of user.access_token as Authorization in headers
        async with self.http.request(
            method="POST",
            url=f"https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api/game/v2/profile/{user.account_id}/client/QueryProfile?profileId=common_core&rvn=-1",
            headers={ 
                "Authorization": f"bearer {user.access_token}",
                "Content-Type": "application/json" 
            },
            json={}
        ) as resp:
            profile_data = await resp.json() 
        
        return profile_data
    
    async def get_friend_codes(self, user: EpicUser, platform: str) -> json:
        # https://fngw-mcp-gc-livefn.ol.epicgames.com/fortnite/api/v2/game/friendcodes/<accountID>/<platform>
        # gets the save the world redeem codes based on the platform you've entered
        # REQUIRES usage of user.access_token as Authorization in headers
        async with self.http.request(
            method="GET",
            url=f"https://fngw-mcp-gc-livefn.ol.epicgames.com/fortnite/api/v2/game/friendcodes/{user.account_id}/{platform}",
            headers={ "Authorization": f"bearer {user.access_token}" }
        ) as resp:
            codes_data = await resp.json() 
        
        # this always returns some error, im not sure why.
        return codes_data
    
    async def get_locker_data(self, user: EpicUser) -> LockerData:
        # gets locker arrays
        # locker_categories - the locker categories we render
        async with self.http.request(
            method="POST",
            url=f"https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api/game/v2/profile/{user.account_id}/client/QueryProfile?profileId=athena",
            headers={ 
                "Authorization": f"bearer {user.access_token}", 
                "Content-Type": "application/json" 
            },
            json={}
        ) as resp:
            athena_data = await resp.json() 
            locker_data = LockerData()
            exclusive_cosmetics = []
            popular_cosmetics = []
            if "profileChanges" not in athena_data:
                return LockerData()
            
            try:
                with open('exclusive.txt', 'r', encoding='utf-8') as f:
                    exclusive_cosmetics = [i.strip() for i in f.readlines()]
            except FileNotFoundError:
                print("Warning: exclusive.txt not found.")
            
            try:
                with open('most_wanted.txt', 'r', encoding='utf-8') as f:
                    popular_cosmetics = [i.strip() for i in f.readlines()]
            except FileNotFoundError:
                print("Warning: most_wanted.txt not found.")

            # getting owned items list
            for item_data in athena_data['profileChanges'][0]['profile']['items']:
                item_template_id = athena_data['profileChanges'][0]['profile']['items'][item_data]['templateId']

                # battle royale cosmetic
                if item_template_id.startswith('Athena'):
                    locker_category = item_template_id.split(':')[0]
                    lowercase_cosmetic_id = item_template_id.split(':')[1]
                    locker_data.unlocked_styles[lowercase_cosmetic_id] = []

                    # special locker categories
                    if 'AthenaExclusive' not in locker_data.cosmetic_categories:
                        locker_data.cosmetic_categories['AthenaExclusive'] = []
                        locker_data.cosmetic_array['AthenaExclusive'] = []
                        locker_data.cosmetic_categories['AthenaExclusive'].append(lowercase_cosmetic_id)
                    
                    if 'AthenaPopular' not in locker_data.cosmetic_categories:
                        locker_data.cosmetic_categories['AthenaPopular'] = []
                        locker_data.cosmetic_array['AthenaPopular'] = []
                        locker_data.cosmetic_categories['AthenaPopular'].append(lowercase_cosmetic_id)
                    
                    # save the world cosmetic
                    if 'HomebaseBannerIcons' not in locker_data.cosmetic_categories:
                        locker_data.cosmetic_categories['HomebaseBannerIcons'] = []
                        locker_data.cosmetic_array['HomebaseBannerIcons'] = []
                        locker_data.cosmetic_categories['HomebaseBannerIcons'].append(lowercase_cosmetic_id)

                    # adding the categories found to the locker data for later
                    if locker_category not in locker_data.cosmetic_categories:
                        locker_data.cosmetic_categories[locker_category] = []
                        locker_data.cosmetic_array[locker_category] = []

                    # adding the cosmetic id itself to the locker categories
                    locker_data.cosmetic_categories[locker_category].append(lowercase_cosmetic_id)

            # listing the owned unlocked styles for each cosmetic
            for item_id, item_data in athena_data['profileChanges'][0]['profile']['items'].items():
                template_id = item_data.get('templateId', '')
                if template_id.startswith('Athena'):
                    lowercase_cosmetic_id = template_id.split(':')[1]

                    # adding the cosmetic to the "unlocked styles"
                    if lowercase_cosmetic_id not in locker_data.unlocked_styles:
                        locker_data.unlocked_styles[lowercase_cosmetic_id] = []
        
                    attributes = item_data.get('attributes', {})
                    variants = attributes.get('variants', [])
                    for variant in variants:
                        # adding the cosmetic's owned styles
                        locker_data.unlocked_styles[lowercase_cosmetic_id].extend(variant.get('owned', []))

            # getting banners
            common_profile_data = await self.get_common_profile(user)
            if common_profile_data:
                # common profile found
                for profileChange in common_profile_data["profileChanges"]:
                    profile_items = profileChange["profile"]["items"]

                    # checking every item
                    for item_key, item_value in profile_items.items():
                        cosmetic_template_id = item_value.get("templateId", "")
                        if cosmetic_template_id:
                            lowercase_banner_id = cosmetic_template_id.split(':')[1]
                            # adding the banner to the owned banners list
                            if lowercase_banner_id not in locker_data.homebase_banners:
                                locker_data.homebase_banners[lowercase_banner_id] = []

            # now lets handle cosmetic crap
            for category in locker_data.cosmetic_categories:
                if category == "AthenaPopular" or category == "AthenaExclusive":
                    continue
            
                try:
                    listoflists = []
                    for _i in range(0, len(locker_data.cosmetic_categories[category]), 50):
                        sublist = locker_data.cosmetic_categories[category][_i:_i+50]
                        listoflists.append(sublist)

                    for cosm in listoflists:
                        cosmetic_by_id_data = requests.get('https://fortnite-api.com/v2/cosmetics/br/search/ids?language=en&id={}'.format('&id='.join(cosm)))
                        for cosmetic_found in cosmetic_by_id_data.json()['data']:
                            if category == 'AthenaDance':
                                if cosmetic_found['type']['value'] != 'emote':
                                    if cosmetic_found['id'] not in exclusive_cosmetics:
                                        continue

                            make_mythic = False
                            if cosmetic_found['id'] in exclusive_cosmetics:
                                make_mythic = True
                                # Pink Ghoul Trooper
                                if cosmetic_found['id'].lower() == 'cid_029_athena_commando_f_halloween':
                                    make_mythic = False
                                    if 'Mat3' in locker_data.unlocked_styles.get('cid_029_athena_commando_f_halloween', []):
                                        make_mythic = True
                            
                                # Purple Skull Trooper
                                if cosmetic_found['id'].lower() == 'cid_030_athena_commando_m_halloween':
                                    make_mythic = False
                                    if 'Mat1' in locker_data.unlocked_styles.get('cid_030_athena_commando_m_halloween', []):
                                        make_mythic = True                            
                            
                                # Stage 5 Omega Lights
                                if cosmetic_found['id'].lower() == 'cid_116_athena_commando_m_carbideblack':
                                    make_mythic = False
                                    if 'Stage5' in locker_data.unlocked_styles.get('cid_116_athena_commando_m_carbideblack', []):
                                        make_mythic = True
                                
                                # Gold Midas
                                if cosmetic_found['id'].lower() == 'cid_694_athena_commando_m_catburglar':
                                    make_mythic = False
                                    if 'Stage4' in locker_data.unlocked_styles.get('cid_694_athena_commando_m_catburglar', []):
                                        make_mythic = True
                            
                                # Gold Meowscles
                                if cosmetic_found['id'].lower() == 'cid_693_athena_commando_m_buffcat':
                                    make_mythic = False
                                    if 'Stage4' in locker_data.unlocked_styles.get('cid_693_athena_commando_m_buffcat', []):
                                        make_mythic = True
                            
                                # Gold TNtina
                                if cosmetic_found['id'].lower() == 'cid_691_athena_commando_f_tntina':
                                    make_mythic = False
                                    if 'Stage7' in locker_data.unlocked_styles.get('cid_691_athena_commando_f_tntina', []):
                                        make_mythic = True
                                    
                                # Gold Skye
                                if cosmetic_found['id'].lower() == 'cid_690_athena_commando_f_photographer':
                                    make_mythic = False
                                    if 'Stage4' in locker_data.unlocked_styles.get('cid_690_athena_commando_f_photographer', []):
                                        make_mythic = True
                                    
                                # Gold Agent Peely
                                if cosmetic_found['id'].lower() == 'cid_701_athena_commando_m_bananaagent':
                                    make_mythic = False
                                    if 'Stage4' in locker_data.unlocked_styles.get('cid_701_athena_commando_m_bananaagent', []):
                                        make_mythic = True
                            
                                # World Cup Fishtick
                                if cosmetic_found['id'].lower() == 'cid_315_athena_commando_m_teriyakifish':
                                    make_mythic = False
                                    if 'Stage3' in locker_data.unlocked_styles.get('cid_315_athena_commando_m_teriyakifish', []):
                                        make_mythic = True
                            
                                # Mate Black Masterchief
                                if cosmetic_found['id'].lower() == 'cid_971_athena_commando_m_jupiter_s0z6m':
                                    make_mythic = False
                                    if 'Mat2' in locker_data.unlocked_styles.get('cid_971_athena_commando_m_jupiter_s0z6m', []):
                                        make_mythic = True
                            
                                if make_mythic == True:
                                    cosmetic_found['rarity']['value'] = 'mythic'
                            
                            cosmetic_info = FortniteCosmetic()
                            cosmetic_info.cosmetic_id = cosmetic_found['id']
                            cosmetic_info.name = cosmetic_found['name']
                            cosmetic_info.small_icon = cosmetic_found['images']['smallIcon']
                            cosmetic_info.icon = cosmetic_found['images']['icon']
                            cosmetic_info.backend_value = category
                            cosmetic_info.rarity_value = cosmetic_found['rarity']['value']
                            cosmetic_info.is_banner = False
                            cosmetic_info.is_exclusive = make_mythic
                            cosmetic_info.is_popular = cosmetic_found['id'] in popular_cosmetics
                            cosmetic_info.unlocked_styles = locker_data.unlocked_styles[cosmetic_found['id'].lower()]

                            if cosmetic_info.is_popular:
                                locker_data.cosmetic_array['AthenaPopular'].append(cosmetic_info)
                        
                            locker_data.cosmetic_array[category].append(cosmetic_info) 
                            
                            # now exclusive
                            if make_mythic:
                                locker_data.cosmetic_array['AthenaExclusive'].append(cosmetic_info)

                except Exception as e:
                    continue


            # handle banners
            banners_data = requests.get('https://fortnite-api.com/v1/banners')
            for fn_banner in banners_data.json()['data']:
                banner_lower_id = fn_banner['id'].lower()
                if banner_lower_id not in locker_data.homebase_banners:
                    # banner isn't owned
                    continue
                    
                make_mythic = False
                icon = fn_banner['images']['icon']
                rarity = 'uncommon'
                if fn_banner['id'] in exclusive_cosmetics:
                    rarity = 'mythic'
                                    
                # for future
                cosmetic_info = FortniteCosmetic()
                cosmetic_info.cosmetic_id = fn_banner['id']
                cosmetic_info.name = fn_banner['devName']
                cosmetic_info.small_icon = fn_banner['images']['smallIcon']
                cosmetic_info.icon = fn_banner['images']['icon']
                cosmetic_info.rarity_value = rarity
                cosmetic_info.backend_value = 'HomebaseBannerIcons'
                cosmetic_info.is_banner = True
                cosmetic_info.is_exclusive = make_mythic
                cosmetic_info.is_popular = fn_banner['id'] in popular_cosmetics
                
                locker_data.cosmetic_array['HomebaseBannerIcons'].append(cosmetic_info)      
                
                # now exclusive ones
                if make_mythic:
                    locker_data.cosmetic_array['AthenaExclusive'].append(cosmetic_info)

            # sorting exclusives category
            locker_data.cosmetic_array['AthenaExclusive'].sort(
                key=lambda cosmetic: exclusive_cosmetics.index(cosmetic.cosmetic_id) 
                if cosmetic.cosmetic_id in exclusive_cosmetics 
                else float('inf')
            )

            # returning back the locker data
        return locker_data
    
    async def get_seasons_message(self, user: EpicUser) -> str:
        async with self.http.request(
            method="POST",
            url=f"https://fortnite-public-service-prod11.ol.epicgames.com/fortnite/api/game/v2/profile/{user.account_id}/client/QueryProfile?profileId=athena",
            headers={ 
                "Authorization": f"bearer {user.access_token}", 
                "Content-Type": "application/json" 
            },
            json={}
        ) as resp:
            athena_data = await resp.json()
            past_seasons = {}
            seasons_info = []
            
            # seasons infos
            past_seasons = athena_data.get("profileChanges", [{}])[0].get("profile", {}).get("stats", {}).get("attributes", {}).get("past_seasons", [])
            total_wins = sum(season.get("numWins", 0) for season in past_seasons)
            total_matches = sum(
                season.get("numHighBracket", 0) + season.get("numLowBracket", 0) + 
                season.get("numHighBracket_LTM", 0) + season.get("numLowBracket_LTM", 0) + 
                season.get("numHighBracket_Ar", 0) + season.get("numLowBracket_Ar", 0) 
                for season in past_seasons
            )

            curses = athena_data['profileChanges'][0]['profile']['stats']['attributes']
            cursesinfo = {
                'level': curses.get('level', 1),
                'book_level': curses.get('book_level', 1)
            }
            
            for season in past_seasons:
                seasons_info.append(f"""
#️⃣Season {season.get('seasonNumber', 1)}
› Level: {season.get('seasonLevel', '1')}
› Battle Pass: {bool_to_emoji(season.get('purchasedVIP', False))}
› Wins: {season.get('numWins', 0)}
            """)

            seasons_info_embeds = seasons_info
            seasons_info_message = "Previous Seasons History:\n" + "\n".join(seasons_info_embeds)
            seasons_info_message += f"\nCurrent Season:\n› Level: {cursesinfo['level']}\n› Battle Pass Level: {cursesinfo['book_level']}"

        return seasons_info_message