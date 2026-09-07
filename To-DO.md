# To-Do Tasks

- Authentication
    - Enforce roles: Administrator, Assessor - conducts an assessment, Owner - can manage allocated assets, controls, risks, tasks
- User Interface
    - Create custom style for unified form formatting. I.e. same size for assessment_code, risk_code
- Assessment management
	- Address change of assessment_type: For example from RISK to CONTROL
	- Avoid duplication of AssessmentItem with same risk or control - unique
	- Improve initialize_assessment: currently AssessmentItems generated for all controls or risks. Use AssessmentControlScope or AssessmentRiskScope to create specific controls or risks: By owner, By asset
	- problem: new risk or control does not auto-addes to in-progress assessments with "include_all"
	- Who ownes AssessmentItem (i.e. ControlMaturityAssessment, RiskAssessment, ControlTest) - control Owner or Assessor?
	