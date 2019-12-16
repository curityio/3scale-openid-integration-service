## 3Scale OpenID Integration Wrapper

This sample python application acts as a wrapper of 3Scale's REST API and Red Hat SSO integration.
It translates incoming requests to RESTCONF which is used by Curity's configuration admin API.

### Setup Explanation

3Scale communicates with an OpenID provider using one of two proprietary ways:
 - [Rest API](https://github.com/3scale/zync/tree/master/examples/rest-api)
 - Red Hat SSO, using the ClientRepresentation found [here](https://access.redhat.com/webassets/avalon/d/red-hat-single-sign-on/version-7.0.0/restapi/)

Both these ways use the OpenID Issuer as base url. Since Curity's Rest API is served under another port than the OpenID Server, we would need to proxy those requests to the RESTCONF API.

This can be done using several techniques, as an example, we ll use nginx. So the full picture will look like this:
```
+------------+            +------------+
|   3Scale   | -------- > |   Nginx    | -------------------
+------------+            +------------+                    |
                        8443    |                           | 8443 (<issuer>/clients)
                                |                           |
                                ↓                           ↓
                          +------------+     6749   +-------------+   
                          |   Curity   | < -------- |   Wrapper   | 
                          +------------+            +-------------+
```
The Ngnix configuration for this example looks like this:
```

        location /~/clients {
            proxy_pass "http://<wrapper_host>:5555";
        }

        location /~/clients-registrations/default {
            proxy_pass "http://<wrapper_host>:5555";
        }

        location / {
            proxy_pass "https://<curity_ip>:<curity_port>";
        }
```

### Configuration

First, install the requirements `pip install -r requirements.txt`

Edit the server.py file and configure the corresponding values in the config section:
```
oauth_profile_id = "authorization"                  # Name of the Token Profile
restconf_api_username = "admin"                     # Admin user username
restconf_api_password = "Password1"                 # Admin user password
restconf_api_host = "https://localhost:6749"        # Admin API base url
default_scopes = ["read", "write"]                  # Default scopes (can be empty)
issuer_path  = "/~"                                 # Curity's oauth-anonymous endpoint path
introspection_host = "http://localhost:8443"        # Curity base URL
introspection_path = "/oauth/v2/oauth-introspect"   # Curity's introspection endpoint path
introspection_client_id = "3scale_rest_api_wrapper" # Client ID for introspection
introspection_client_secret = "Password2"           # Client secret
```
The client configured in this section must be allowed to do introspection.

Another client will be needed, that can do client_credentilas. This second client will be used by 3Scale to get an access token for further communication with this wrapper.


#### Curity configuration
- Curity's Base URL has to be the one that nginx proxies (configure it under System/General)
- Create 2 clients, one for introspection which is configured in the python app and one with client_credentials which is configured in 3Scale
- Change the token endpoint path to be `<issuer>/token_endpoint` this is because currently there is a bug in 3Scale where the token_endpoint is not properly readed from the openid-metadata

In order to be able to issue tokens for applications created in 3Scale, the access tokens have to be in JWT format.
To enable this, set the flag "Use Access Token As JWT" in the Token Profile/Token Issuers page.


### Supported Requests

1. Create/Update a client

3Scale calls either `<openid_issuer>/clients/<client_id>` or `<openid_issuer>/clients-registrations/default/<client_id>`

Both are trunslated to a PUT to 
`https://<curity_host>:<admin_port>/admin/api/restconf/data/base:profiles/base:profile=<token_profile_id>,oauth-service/base:settings/profile-oauth:authorization-server/profile-oauth:client-store/profile-oauth:config-backed/client=<client_id>"`

Keep in mind that the clients created do not have any authenticators selected so if you need to add more specific configuration you can modify the corresponding JSON Object as needed.

2. Delete a client

3Scale calls either `<openid_issuer>/clients/<client_id>` or `<openid_issuer>/clients-registrations/default/<client_id>` with HTTP DELETE.
This is translated to a DELETE request on Curity's RESTCONF API.

`https://<curity_host>:<admin_port>/admin/api/restconf/data/base:profiles/base:profile=<token_profile_id>,oauth-service/base:settings/profile-oauth:authorization-server/profile-oauth:client-store/profile-oauth:config-backed/client=<client_id>"`