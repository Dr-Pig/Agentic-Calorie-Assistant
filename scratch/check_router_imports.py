try:
    from app.runtime.application.v2_bundle1_service import V2Bundle1OnboardingPayload, execute_bundle1_turn
    from app.web.v2_routes import router
    print("Router and Service imports successful!")
except Exception as e:
    import traceback
    traceback.print_exc()
