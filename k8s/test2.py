
from kubernetes import client, config

# 加载配置文件
config.load_kube_config(config_file="/home/lingwen/Desktop/kube/config")
# 如果在k8s的本机上，或者配置文件是~/.kube/config，则可以直接加载配置
# config.load_kube_config()

# 创建API对象
api_instance = client.CoreV1Api()

# 使用API对象执行操作，例如列出所有命名空间
namespace_list = api_instance.list_namespace()
for namespace in namespace_list.items:
    print(namespace.metadata.name)