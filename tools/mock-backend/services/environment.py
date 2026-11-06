"""
anthill-environment: GET /environment/<application>/<version>
Returns environment variables for the application; the runtime requires "discovery".
"""


def handle(ctx, rest):
    # rest = [application_name, application_version]
    return {
        "discovery": ctx.app.service_url("discovery"),
    }
