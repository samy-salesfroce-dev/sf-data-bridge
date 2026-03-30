from simple_salesforce import Salesforce, SalesforceAuthenticationFailed

def authenticate(username, password, security_token, domain):
    """
    Authenticates with Salesforce using Username, Password, and Security Token.
    Domain should be 'login' for Production/Developer, or 'test' for Sandboxes.
    """
    try:
        sf = Salesforce(
            username=username,
            password=password,
            security_token=security_token,
            domain=domain
        )
        return sf, None
    except SalesforceAuthenticationFailed as e:
        return None, str(e)
    except Exception as e:
        return None, f"An unexpected error occurred: {str(e)}"

def verify_session(sf_instance):
    """
    Verifies if a Salesforce connection is still alive.
    """
    try:
        result = sf_instance.query("SELECT Id FROM User LIMIT 1")
        return True
    except:
        return False
