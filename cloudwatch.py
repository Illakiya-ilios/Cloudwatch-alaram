import boto3

# ===========================
# INPUTS
# ===========================
INSTANCE_ID = "i-023be34ed5c046d70"
INSTANCE_NAME = "Document-Analysis"
ACCOUNT_NAME = "WeAlwin"
SNS_TOPIC_ARN = "arn:aws:sns:ap-south-1:850995535715:cloudwatch_alaram"  
REGION = "ap-south-1"

cloudwatch = boto3.client('cloudwatch', region_name=REGION)

# ===========================
# FUNCTION TO CREATE ALARMS
# ===========================
def create_alarm(metric_name, threshold, level, metric_label, namespace="AWS/EC2", extra_dimensions=None):
    """
    Creates a CloudWatch alarm with formatted name:
    <Level>_<AccountName>_<Metric>_Reaches_<Threshold>%_<InstanceName>_(<InstanceID>)
    """
    if extra_dimensions is None:
        extra_dimensions = [{'Name': 'InstanceId', 'Value': INSTANCE_ID}]

    alarm_name = f"{level}_{ACCOUNT_NAME}_{metric_label}_Reaches_{threshold}%_{INSTANCE_NAME}_({INSTANCE_ID})"

    params = {
        "AlarmName": alarm_name,
        "MetricName": metric_name,
        "Namespace": namespace,
        "Statistic": "Average",
        "Period": 300,
        "EvaluationPeriods": 1,
        "Threshold": threshold,
        "ComparisonOperator": "GreaterThanOrEqualToThreshold",
        "Dimensions": extra_dimensions,
    }

    if SNS_TOPIC_ARN:
        params["AlarmActions"] = [SNS_TOPIC_ARN]

    cloudwatch.put_metric_alarm(**params)
    print(f"[+] Created Alarm: {alarm_name}")


# ==================================================
# CPU ALARMS (AWS/EC2)
# ==================================================
cpu_thresholds = [(90, "Critical"), (80, "Warning"), (79, "Normal")]
for threshold, level in cpu_thresholds:
    create_alarm(
        metric_name="CPUUtilization",
        threshold=threshold,
        level=level,
        metric_label="CPU",
        namespace="AWS/EC2"
    )

# ==================================================
# MEMORY ALARMS (CWAgent)
# ==================================================
mem_extra_dimensions = [
    {'Name': 'InstanceId', 'Value': INSTANCE_ID},
    {'Name': 'ImageId', 'Value': '*'},
    {'Name': 'InstanceType', 'Value': '*'}
]

mem_thresholds = [(90, "Critical"), (80, "Warning"), (79, "Normal")]
for threshold, level in mem_thresholds:
    create_alarm(
        metric_name="mem_used_percent",
        threshold=threshold,
        level=level,
        metric_label="Memory",
        namespace="CWAgent",
        extra_dimensions=mem_extra_dimensions
    )



def get_root_disk_dimensions():
    metrics = cloudwatch.list_metrics(
        Namespace="CWAgent",
        MetricName="disk_used_percent"
    )

    for metric in metrics.get("Metrics", []):
        dims = {d["Name"]: d["Value"] for d in metric["Dimensions"]}

        # Must match this instance AND root path
        if dims.get("InstanceId") == INSTANCE_ID and dims.get("path") == "/":
            return dims

    return None


print("[*] Fetching root disk metric from CloudWatch...")
root_dims = get_root_disk_dimensions()

if not root_dims:
    print("[!] No disk metrics found for path '/'. Is the CloudWatch agent configured?")
else:
    print(f"[+] Found root disk: device={root_dims.get('device')}, fstype={root_dims.get('fstype')}")


# Create alarms only if data found
if root_dims:
    disk_thresholds = [(90, "Critical"), (80, "Warning"), (79, "Normal")]

    for threshold, level in disk_thresholds:
        extra_dimensions = [
            {'Name': 'InstanceId', 'Value': INSTANCE_ID},
            {'Name': 'path', 'Value': '/'},
            {'Name': 'device', 'Value': root_dims.get("device")},
            {'Name': 'fstype', 'Value': root_dims.get("fstype")},
        ]

        create_alarm(
            metric_name="disk_used_percent",
            threshold=threshold,
            level=level,
            metric_label="Disk",
            namespace="CWAgent",
            extra_dimensions=extra_dimensions
        )

print("\n[✔] All alarms created successfully!")
