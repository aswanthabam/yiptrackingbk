from rest_framework.views import APIView
from db.models import Organization, UserOrgLink, District, Zone
from utils.response import CustomResponse
from utils.authentication import JWTUtils
from django.db.models import Count, Sum, Value, IntegerField, Case, When, F
from django.db.models.functions import Coalesce, Concat
from utils.utils import ImportCSV,CommonUtils


class IdeaCountListAPI(APIView):
    def get(self,request):
        if not JWTUtils.is_jwt_authenticated(request):
            return CustomResponse(general_message='Unauthorized').get_failure_response()
        zone_id = request.query_params.get('zone_id')
        district_id = request.query_params.get('district_id')
        org_type = request.query_params.get('org_type')
        data_type = request.query_params.get('type') # organization, district, zone, intern
        data_type = data_type if data_type else 'organization'
        is_pagination = not (request.query_params.get('is_pagination', '').lower() in ('false','0'))

        orgs = Organization.objects.all()
        if zone_id:
            orgs = orgs.filter(district_id__zone_id=zone_id)
        if district_id:
            orgs = orgs.filter(district_id=district_id)
        if org_type:
            orgs = orgs.filter(org_type=org_type)
        if data_type == 'organization':
            data = orgs.values('id').annotate(
                name=Concat(F('code'),Value(' - '),F('title')),
                pre_registration=Coalesce(Sum('pre_registration'),Value(0)),
                vos_completed=Coalesce(Sum('vos_completed'),Value(0)),
                group_formation=Coalesce(Sum('group_formation'),Value(0)),
                idea_submissions=Coalesce(Sum('idea_submissions'),Value(0)),
            ).values('name','pre_registration','vos_completed','group_formation','idea_submissions')
        if data_type == 'district':
            data = orgs.values('district_id').annotate(
                district=F('district_id__name'),
                zone=F('district_id__zone_id__name'),
                pre_registration=Coalesce(Sum('pre_registration'),Value(0)),
                vos_completed=Coalesce(Sum('vos_completed'),Value(0)),
                group_formation=Coalesce(Sum('group_formation'),Value(0)),
                idea_submissions=Coalesce(Sum('idea_submissions'),Value(0)),
            ).values('district','zone','pre_registration','vos_completed','group_formation','idea_submissions')
        if data_type == 'zone':
            data = orgs.values('district_id__zone_id').annotate(
                zone=F('district_id__zone_id__name'),
                pre_registration=Coalesce(Sum('pre_registration'),Value(0)),
                vos_completed=Coalesce(Sum('vos_completed'),Value(0)),
                group_formation=Coalesce(Sum('group_formation'),Value(0)),
                idea_submissions=Coalesce(Sum('idea_submissions'),Value(0)),
            ).values('zone','pre_registration','vos_completed','group_formation','idea_submissions')
        if data_type == 'intern':
            data = UserOrgLink.objects.annotate(
                email=F('user_id__email'),
                full_name=Concat(F('user_id__first_name'), F('user_id__last_name')),
                pre_registration=Coalesce(Sum('org_id__pre_registration'),Value(0)),
                vos_completed=Coalesce(Sum('org_id__vos_completed'),Value(0)),
                group_formation=Coalesce(Sum('org_id__group_formation'),Value(0)),
                idea_submissions=Coalesce(Sum('org_id__idea_submissions'),Value(0)),
            )
            if org_type:
                data = data.filter(org_id__org_type=org_type)
            if district_id:
                data = data.filter(org_id__district_id=district_id)
            if zone_id:
                data = data.filter(org_id__district_id__zone_id=zone_id)
            data = data.values('full_name','email','pre_registration','vos_completed','group_formation','idea_submissions')
        if is_pagination:
            paginated_queryset = CommonUtils.get_paginated_queryset(
                data, 
                request, 
                search_fields=[], 
                sort_fields={
                    'pre_registration':'pre_registration',
                    'vos_completed':'vos_completed',
                    'group_formation':'group_formation',
                    'idea_submissions':'idea_submissions'
                },
                is_pagination=True
            )
            return CustomResponse().paginated_response(data=list(paginated_queryset.get('queryset')), pagination=paginated_queryset.get('pagination'))
        return CustomResponse(response=data).get_success_response()

class TotalIdeaCountAPI(APIView):
    def get(self,request):
        if not JWTUtils.is_jwt_authenticated(request):
            return CustomResponse(general_message='Unauthorized').get_failure_response()
        zone_id = request.query_params.get('zone_id')
        district_id = request.query_params.get('district_id')
        org_type = request.query_params.get('org_type')
        orgs = Organization.objects.all()
        if zone_id:
            orgs = orgs.filter(district_id__zone_id=zone_id)
        if district_id:
            orgs = orgs.filter(district_id=district_id)
        if org_type:
            orgs = orgs.filter(org_type=org_type)
        data = orgs.aggregate(
            pre_registration=Coalesce(Sum('pre_registration'),Value(0)),
            vos_completed=Coalesce(Sum('vos_completed'),Value(0)),
            group_formation=Coalesce(Sum('group_formation'),Value(0)),
            idea_submissions=Coalesce(Sum('idea_submissions'),Value(0)),
        )
        return CustomResponse(response=data).get_success_response()

class ImportOrgCSVAPI(APIView):
    def post(self, request):
        if not JWTUtils.is_jwt_authenticated(request):
            return CustomResponse(general_message='Unauthorized').get_failure_response()
        try:
            file_obj = request.FILES["file"]
        except KeyError:
            return CustomResponse(
                general_message="File not found."
            ).get_failure_response()

        excel_data = ImportCSV()
        excel_data = excel_data.read_excel_file(file_obj)

        if not excel_data:
            return CustomResponse(
                general_message="Empty csv file."
            ).get_failure_response()

        temp_headers = [
            "code",
            "pre_registration",
            "vos_completed",
            "group_formation",
            "idea_submissions",
        ]
        first_entry = excel_data[0]
        for key in temp_headers:
            if key not in first_entry:
                return CustomResponse(
                    general_message=f"{key} does not exist in the file."
                ).get_failure_response()

        excel_data = [row for row in excel_data if any(row.values())]
        # print(json.dumps(excel_data, indent=4))
        try:
            for row in excel_data[1:]:
                org = Organization.objects.filter(code=row.get('code')).first()
                if org:
                    org.pre_registration += row.get('pre_registration')
                    org.vos_completed += row.get('vos_completed')
                    org.group_formation += row.get('group_formation')
                    org.idea_submissions += row.get('idea_submissions')
                    org.save()
                    continue
                return CustomResponse(general_message=f"Organization with code {row.get('code')} does not exist.").get_failure_response()
            return CustomResponse(general_message=f"Successfully imported {len(excel_data[1:])} rows.").get_success_response()
        except:
            return CustomResponse(
                general_message="Error occured while importing data."
            ).get_failure_response()