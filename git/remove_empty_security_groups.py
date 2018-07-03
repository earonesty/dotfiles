import boto3

def main():
    ec2 = boto3.resource('ec2')
    sgs = get_security_map(ec2)
    delete_unused_groups(sgs)
    audit_open_ports(sgs)

def decorate_security_group(i):
    if i.tags:
        i.tag = {e["Key"]:e["Value"] for e in i.tags}
    else:
        i.tag = {}

    i.dependents = {}
    if "Name" not in i.tag and i.group_name:
        i.create_tags(DryRun=False, Tags=[{"Key":"Name","Value":i.group_name}])
        i.tag["Name"] = i.group_name

    i.name = i.tag.get("Name","")


def decorate_instance(i):
    if i.tags:
        i.tag = {e["Key"]:e["Value"] for e in i.tags}
    else:
        i.tag = {}

    if i.security_groups:
        i.security_group = {e["GroupId"]:e["GroupName"] for e in i.security_groups}
    else:
        i.security_group = {}

def decorate_network_interface(i):
    if i.groups:
        i.security_group = {e["GroupId"]:e["GroupName"] for e in i.groups}
    else:
        i.security_group = {}

def get_security_map(ec2):
    sglist = ec2.security_groups.all()
    sgs={}
    for sg in sglist:
        decorate_security_group(sg)
        sgs[sg.group_id] = sg

    for i in ec2.instances.all():
        decorate_instance(i)
        for sgid in i.security_group.keys():
            sgs[sgid].dependents[i.id] = i

    for i in ec2.network_interfaces.all():
        decorate_network_interface(i)
        for sgid in i.security_group.keys():
            sgs[sgid].dependents[i.id] = i

    return sgs

def delete_unused_groups(sgs):
    for sg in sgs.values():
        if not sg.dependents and sg.name != 'default':
            sg.delete()
        else:
            print(sg.group_id, sg.group_name, sg.dependents)

def print_open_ports(sgs):
    for sg in sgs.values():
        if not sg.dependents and sg.name != 'default':
            sg.delete()
        else:
            print(sg.group_id, sg.group_name, sg.dependents)

if __name__ == "__main__":
    main()
