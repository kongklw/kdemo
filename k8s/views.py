from rest_framework.views import APIView
from rest_framework.response import Response
from kubernetes import client, config
import time
import kubernetes.client
from kubernetes.client.rest import ApiException
from pprint import pprint
# Configs can be set in Configuration class directly or using helper utility
config.load_kube_config()

v1 = client.CoreV1Api()


configuration = kubernetes.client.Configuration()
# Configure API key authorization: BearerToken
# configuration.api_key['authorization'] = 'YOUR_API_KEY'
# Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
# configuration.api_key_prefix['authorization'] = 'Bearer'
configuration.host = "http://localhost"
'''
[root@master ~]# kubectl describe secrets dashboard-admin-token-w6586
Name:         dashboard-admin-token-w6586
Namespace:    default
Labels:       <none>
Annotations:  kubernetes.io/service-account.name: dashboard-admin
              kubernetes.io/service-account.uid: 58cf3ed7-9539-47df-9669-d6e58fc85117

Type:  kubernetes.io/service-account-token

Data
====
ca.crt:     1025 bytes
namespace:  7 bytes
token:      eyJhbGciOiJSUzI1NiIsImtpZCI6InQzTFNESWY3Wi11X096RFBYUnJTM0V3d2k5dEp1OFViYkItZU9TTEhSREEifQ.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJkZWZhdWx0Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6ImRhc2hib2FyZC1hZG1pbi10b2tlbi13NjU4NiIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50Lm5hbWUiOiJkYXNoYm9hcmQtYWRtaW4iLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC51aWQiOiI1OGNmM2VkNy05NTM5LTQ3ZGYtOTY2OS1kNmU1OGZjODUxMTciLCJzdWIiOiJzeXN0ZW06c2VydmljZWFjY291bnQ6ZGVmYXVsdDpkYXNoYm9hcmQtYWRtaW4ifQ.vdgUD5qpABnDT9PFFueEZ8JuvM-Ui1IpFEmFdLDrKPYgO0n1OHoF4Ie_2N9e1Qvk5WaWJfmkH2-72Ob8njeXtT31NNWOk3HEXJgF4Oa8iEI7lEArdJciZZm2R6Yf6HqikiohkZJVk3XHY-RecR2sIOTlnSkJvx0CrF5LcGhPFT8VsT69zK8x8Lr99e0h4zR0Kam2FKZHLpc_KD-W1sFYIvAdgtkdwKCBzf_5B_GKKs6eaTcVyeeuUp2B__GJWP1qzcjaD5uLN4q3pdrNhy8uVsUDKzvR_7rVAUZQ4n3LCjW5lrsXgpgiR3Fjdr6YA1uSeZrTh0txyn_AB7gVSEToQw


'''

class Pos(APIView):
    def get(self, request, *args, **kwargs):

        try:
            print("Listing pods with their IPs:")
            ret = v1.list_pod_for_all_namespaces(watch=False)
            for i in ret.items:
                print("%s\t%s\t%s" % (i.status.pod_ip, i.metadata.namespace, i.metadata.name))
            response = {"code": 200, "data": 'ok', "msg": "success"}
            return Response(response)
        except Exception as exc:
            response = {"code": 205, "data": None, "msg": str(exc)}
            return Response(response)
