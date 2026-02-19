from enum import Enum

class SeafSchema(str, Enum):
    # Core Services
    DC_REGION = "seaf.company.ta.services.dc_regions"
    DC_AZ = "seaf.company.ta.services.dc_azs"
    DC = "seaf.company.ta.services.dcs"
    DC_OFFICE = "seaf.company.ta.services.dc_offices"
    
    # Network Services
    NETWORK_SEGMENT = "seaf.company.ta.services.network_segments"
    NETWORK = "seaf.company.ta.services.networks"
    NETWORK_LINK = "seaf.company.ta.services.network_links"
    LOGICAL_LINK = "seaf.company.ta.services.logical_links"
    
    # Network Components
    COMPONENT_NETWORK = "seaf.company.ta.components.networks"
    
    # Compute & Infrastructure
    COMPUTE_SERVICE = "seaf.company.ta.services.compute_services"
    CLUSTER_VIRTUALIZATION = "seaf.company.ta.services.cluster_virtualizations"
    K8S = "seaf.company.ta.services.k8s"
    BACKUP = "seaf.company.ta.services.backups"
    MONITORING = "seaf.company.ta.services.monitorings"
    STORAGE = "seaf.company.ta.services.storages"
    HW_STORAGE = "seaf.company.ta.services.hw_storages"
    KB = "seaf.company.ta.services.kb"
    
    # End User
    COMPONENT_SERVER = "seaf.company.ta.components.servers"
    COMPONENT_USER_DEVICE = "seaf.company.ta.components.user_devices"
    
    # K8s Components
    K8S_NAMESPACE = "seaf.company.ta.components.k8s.namespaces"
    K8S_NODE = "seaf.company.ta.components.k8s.nodes"
    K8S_DEPLOYMENT = "seaf.company.ta.components.k8s.deployments"
    K8S_HPA = "seaf.company.ta.components.k8s.hpa"

# Mapping for merged or renamed schemas if needed in future logic
LEGACY_MAPPING = {
    "seaf.ta.services.cluster": SeafSchema.COMPUTE_SERVICE,
}
