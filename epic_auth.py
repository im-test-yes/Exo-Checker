import aiohttp
import asyncio
import os
import platform
import datetime
import json

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

class EpicGenerator:
    def __init__(self) -> None:
        # init the generator
        self.http: aiohttp.ClientSession
        self.user_agent = f"DeviceAuthGenerator/{platform.system()}/{platform.version()}"
        self.access_token = ""

    async def start(self) -> None:
        self.http = aiohttp.ClientSession(headers={"User-Agent": self.user_agent})
        self.access_token = await self.get_access_token()
    
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
            account_info['externalAuths'] = await EpicGenerator.get_external_connections(self, user)

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
        # https://fngw-mcp-gc-livefn.ol.epicgames.com/fortnite/api/v2/game/friendcodes/
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