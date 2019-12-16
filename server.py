import requests
from flask import Flask, jsonify, request, make_response

from oauth.oauth_filter import OAuthFilter

app = Flask(__name__)
refOauth = OAuthFilter(verify_ssl=False)

###################################
#             CONFIG              #
###################################
oauth_profile_id = "oauth-dev"  # Name of the Token Profile
restconf_api_username = "admin"
restconf_api_password = "Password1"
restconf_api_host = "https://localhost:6749"
default_scopes = ["read"]
issuer_path = "/~"
introspection_host = "http://localhost:8444"  # curity domain, can be either direct http(s)://<IP_OR_HOST>:<PORT>
introspection_path = "/oauth/v2/oauth-introspect"
introspection_client_id = "3scale_rest_api_wrapper"
introspection_client_secret = "One4all1"
debug = True
###################################
#             CONFIG              #
###################################

restconf_api_endpoint = "%s/admin/api/restconf/data/base:profiles/base:profile=%s,oauth-service/base:settings/profile-oauth:authorization-server/profile-oauth:client-store/profile-oauth:config-backed/client=%s"


@app.route(issuer_path + "/clients/<client_id>", methods=["PUT"])
@app.route(issuer_path + "/clients-registrations/default/<client_id>", methods=["POST", "PUT"])
@refOauth.protect(scopes=[""])
def create_client(client_id):
    client_id = request.path[request.path.rfind("/") + 1:]
    data = request.json

    if debug:
        print("JSON = %s" % data)

    name = data.get("name", data.get("client_name", ""))
    description = data.get("description", "")
    client_id = data.get("clientId", data.get("client_id", client_id))
    client_secret = data.get("secret", data.get("client_secret", ""))
    redirect_uris = data.get("redirectUris", data.get("redirect_uris", []))
    attributes = data.get("attributes", [])
    enabled = data.get("enabled", True)
    code_flow_enabled = data.get("standardFlowEnabled", False) or "authorization_code" in data.get("grant_types")
    implicit_flow_enabled = data.get("implicitFlowEnabled", False) or "implicit" in data.get("grant_types")
    cc_flow_enabled = data.get("serviceAccountsEnabled", False) or "client_credentials" in data.get("grant_types")
    ropc_flow_enabled = data.get("directAccessGrantsEnabled", False) or "password" in data.get("grant_types")

    if debug:
        print("Got call to update client ID %s with name %s, description = %s, secret = %s, redirect URIs = %s," \
              " attributes = %s, enabled = %s, code flow enabled = %s, implicit flow enabled = %s, cc flow enabled = %s, " \
              "ropc enabled = %s" % (client_id, name, description, client_secret, redirect_uris, attributes, enabled,
                                     code_flow_enabled, implicit_flow_enabled, cc_flow_enabled,
                                     ropc_flow_enabled))

    if len(redirect_uris) == 0 or (len(redirect_uris) == 1 and not redirect_uris[0]) and (
            code_flow_enabled or implicit_flow_enabled):
        redirect_uris = ["https://example.com"]

    capabilities = {}
    scopes = default_scopes

    if code_flow_enabled:
        capabilities['code'] = [None]

    if cc_flow_enabled:
        capabilities['client-credentials'] = [None]

    if implicit_flow_enabled:
        capabilities['implicit'] = [None]

    if ropc_flow_enabled:
        capabilities['resource-owner-password-credentials'] = [None]

    if code_flow_enabled or implicit_flow_enabled:
        scopes.append("openid")

    restconf_data = {
        "profile-oauth:client": {
            "id": client_id,
            "client-name": name,
            "description": description,
            "redirect-uris": redirect_uris,
            "capabilities": capabilities,
            "scope": scopes,
            "enabled": enabled
        }
    }

    if cc_flow_enabled or code_flow_enabled or ropc_flow_enabled:
        restconf_data["profile-oauth:client"]["secret"] = client_secret

    restconf_api_endpoint_of_client = restconf_api_endpoint % (restconf_api_host, oauth_profile_id, client_id)
    yang_json = "application/yang-data+json"
    response = requests.put(restconf_api_endpoint_of_client,
                            json=restconf_data,
                            verify=False,
                            headers={"Content-Type": yang_json, "Accept": yang_json},
                            auth=(restconf_api_username, restconf_api_password))

    if debug:
        print("request body = %s" % response.request.body)
        print("request headers = %s" % response.request.headers)
        print("response status_code = %s" % response.status_code)
        if response.status_code >= 400:
            try:
                print("response body from upstream = %s" % response.json())
            except ValueError:
                pass

    return jsonify(dict(OK=True))


@app.route(issuer_path + "/clients/<client_id>", methods=["DELETE"])
@app.route(issuer_path + "/clients-registrations/default/<client_id>", methods=["DELETE"])
@refOauth.protect(scopes=[""])
def delete_client(client_id):
    client_id = request.path[request.path.rfind("/") + 1:]

    restconf_api_endpoint_of_client = restconf_api_endpoint % (restconf_api_host, oauth_profile_id, client_id)

    response = requests.delete(restconf_api_endpoint_of_client,
                               verify=False,
                               auth=(restconf_api_username, restconf_api_password))
    if debug:
        print("response body = %s" % response.request.body)
        print("response headers = %s" % response.request.headers)

    if response.status_code >= 400:
        try:
            print("response body from upstream = %s" % response.json())
        except ValueError:
            pass

    return make_response('', 204)


refOauth.configure_with_opaque("%s%s" % (introspection_host, introspection_path), introspection_client_id,
                               introspection_client_secret)

if __name__ == '__main__':
    app.url_map.strict_slashes = False
    app.run('0.0.0.0', debug=debug, port=5555)
