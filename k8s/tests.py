# from kubernetes import client, config
#
# # Configs can be set in Configuration class directly or using helper utility
# config.load_kube_config()
#
# v1 = client.CoreV1Api()
# print("Listing pods with their IPs:")
# ret = v1.list_pod_for_all_namespaces(watch=False)
# for i in ret.items:
#     print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))


from __future__ import print_function
import time
import kubernetes.client
from kubernetes.client.rest import ApiException
from pprint import pprint

configuration = kubernetes.client.Configuration()
# Configure API key authorization: BearerToken
configuration.api_key[
    'authorization'] = 'Bearer ' + 'eyJhbGciOiJSUzI1NiIsImtpZCI6InQzTFNESWY3Wi11X096RFBYUnJTM0V3d2k5dEp1OFViYkItZU9TTEhSREEifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJkZWZhdWx0Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6ImRhc2hib2FyZC1hZG1pbi10b2tlbi13NjU4NiIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50Lm5hbWUiOiJkYXNoYm9hcmQtYWRtaW4iLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC51aWQiOiI1OGNmM2VkNy05NTM5LTQ3ZGYtOTY2OS1kNmU1OGZjODUxMTciLCJzdWIiOiJzeXN0ZW06c2VydmljZWFjY291bnQ6ZGVmYXVsdDpkYXNoYm9hcmQtYWRtaW4ifQ.vdgUD5qpABnDT9PFFueEZ8JuvM-Ui1IpFEmFdLDrKPYgO0n1OHoF4Ie_2N9e1Qvk5WaWJfmkH2-72Ob8njeXtT31NNWOk3HEXJgF4Oa8iEI7lEArdJciZZm2R6Yf6HqikiohkZJVk3XHY-RecR2sIOTlnSkJvx0CrF5LcGhPFT8VsT69zK8x8Lr99e0h4zR0Kam2FKZHLpc_KD-W1sFYIvAdgtkdwKCBzf_5B_GKKs6eaTcVyeeuUp2B__GJWP1qzcjaD5uLN4q3pdrNhy8uVsUDKzvR_7rVAUZQ4n3LCjW5lrsXgpgiR3Fjdr6YA1uSeZrTh0txyn_AB7gVSEToQw'
# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['authorization'] = 'Bearer'

# # Defining host is optional and default to http://localhost
# configuration.host = "http://localhost"

# Defining host is optional and default to http://localhost
configuration.host = "https://192.168.147.100:6443"
# Enter a context with an instance of the API kubernetes.client
with kubernetes.client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = kubernetes.client.WellKnownApi(api_client)

    try:
        api_response = api_instance.get_service_account_issuer_open_id_configuration()
        pprint(api_response)
    except ApiException as e:
        print("Exception when calling WellKnownApi->get_service_account_issuer_open_id_configuration: %s\n" % e)
