# Control Assessment Tool + Risk Assessment Tool
CAT (Control Assessment Tool) and RAT (Risk Assessment Tool), short name CaR, is a comprehensive web-based application designed to streamline the management of an organization's control library and risk register as well as support internal and external audits. It uses Django: https://www.djangoproject.com/


## Roles
Administrator - create users, manage groups, tables ( bob x^3 )
Reviewer - review and approve control and risk Assessment, help owner to perform their tasks
Owner - manage control and risks, perform assessments (eugene chebur)
Auditor - review controls and evidence, perform audit steps




### Initial steps
1. Install record change history application: 	pip install django-simple-history
3. Create project: 			django-admin startproject app cat-rat
4. Create application: 		python manage.py startapp car
5. Test functionality: 		python manage.py runserver
6. Setup database: 			python manage.py migrate
7. Add admin:				python manage.py createsuperuser
8. Configure project and app to show custom index page
9. Configure logon page + admin functions
10. Create initial tables: Owner, Asset