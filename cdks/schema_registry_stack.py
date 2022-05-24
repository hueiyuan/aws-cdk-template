from aws_cdk import (
    Stack,
    CfnTag,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_elasticloadbalancingv2 as elbv2,
    aws_route53 as route53
)
from constructs import Construct

from configs import general_config, schema_registry_config

CDK_GENERAL_CONF = general_config.GeneralConfig()
CDK_SR_CONF = schema_registry_config.SchemaRegistryConfig()

with open(CDK_SR_CONF.user_data_shell_path) as f:
    schema_registry_user_data = f.read()

class CdkSchemaRegistryStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, environment:str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        schema_registry_name = f'schema-registry-{environment}'
        schema_registry_instance_profile_name = f'schema-registry-instance-profile-{environment}'
        schema_registry_target_group_name = f'schema-registry-task-group-{environment}'
        schema_registry_dns = f'schema-registry-{environment}.com'
        
        schema_registry_iam_role = iam.CfnRole(self, f'SchemaRegistryRole-{environment}',
            path='/',
            managed_policy_arns = [
                'arn:aws:iam::aws:policy/AmazonMSKFullAccess',
                'arn:aws:iam::aws:policy/CloudWatchFullAccess'
            ],
            assume_role_policy_document={
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Sid': '',
                        'Effect': 'Allow',
                        'Principal': {
                            'Service': [
                                'ec2.amazonaws.com'
                            ]
                        },
                        'Action': [
                            'sts:AssumeRole'
                        ]
                    }
                ]
            },
        )
        
        schema_registry_instance_profile = iam.CfnInstanceProfile(self, f'SchemaRegistryIamInstanceProfile-{environment}',
            instance_profile_name=schema_registry_instance_profile_name,
            roles = [schema_registry_iam_role.ref]
        )
        
        schema_registry_instance = ec2.CfnInstance(self, f'SchemaRegistryInstance-{environment}',
            instance_type=CDK_SR_CONF.instance_type,
            key_name=CDK_GENERAL_CONF.ec2_key_name,
            subnet_id=CDK_GENERAL_CONF.subnet_ids[0],
            security_group_ids=CDK_GENERAL_CONF.security_group,
            image_id=CDK_SR_CONF.ami[environment],
            iam_instance_profile=schema_registry_instance_profile.ref,
            tags=[
                CfnTag(key='Name',value=schema_registry_name),
                CfnTag(key='Cost',value='infra'),
                CfnTag(key='Environment',value=environment)
            ],
            user_data=schema_registry_user_data
        )
        
        schema_registry_target_group = elbv2.CfnTargetGroup(self, f'SchemaRegisgryTargetGroup-{environment}',
            name=schema_registry_target_group_name,
            port=CDK_SR_CONF.service_port,
            protocol='HTTP',
            protocol_version='HTTP1',
            target_type='instance',
            targets=[
                elbv2.CfnTargetGroup.TargetDescriptionProperty(
                    id=schema_registry_instance.ref,
                    port=CDK_SR_CONF.service_port
                )
            ],
            vpc_id=CDK_GENERAL_CONF.vpc_id,
            target_group_attributes=[
                elbv2.CfnTargetGroup.TargetGroupAttributeProperty(
                    key='load_balancing.algorithm.type',
                    value=CDK_SR_CONF.target_group_lb
                )
            ],
            tags=[
                CfnTag(key='Name',value=schema_registry_name),
                CfnTag(key='Cost',value='infra'),
                CfnTag(key='Environment',value=environment)
            ]
        )
        
        schema_registry_dns_record = route53.CfnRecordSet(self, f'SchemaRegistryRecordSet-{environment}',
            hosted_zone_id=CDK_SR_CONF.etl_alb_zone_id,
            name=schema_registry_dns,
            type='A',
            alias_target=route53.CfnRecordSet.AliasTargetProperty(
                dns_name=CDK_SR_CONF.recordset_dns_name,
                hosted_zone_id=CDK_SR_CONF.etl_alb_zone_id,
                evaluate_target_health=False
            ),
        )
        
        schema_registry_listener_rule = elbv2.CfnListenerRule(self, f'SchemaRegistryListenerRule-{environment}',
            priority=1,
            listener_arn=CDK_SR_CONF.linstener_arn,
            actions = [
                elbv2.CfnListenerRule.ActionProperty(
                    type='forward',
                    target_group_arn=schema_registry_target_group.ref
                )
            ],
            conditions = [
                elbv2.CfnListenerRule.RuleConditionProperty(
                    field='host-header',
                    host_header_config = elbv2.CfnListenerRule.HostHeaderConfigProperty(
                        values=[schema_registry_dns_record.ref]
                    ),
                )
            ]
        )
        
