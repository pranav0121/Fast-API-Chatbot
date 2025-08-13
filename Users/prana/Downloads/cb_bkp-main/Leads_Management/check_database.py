#!/usr/bin/env python3
# Backend-only implementation. No frontend/static logic.
"""
Database Checker Script
This script helps you view and analyze the data stored in your lead management database.
"""

import json
from datetime import datetime
from database import get_db_session
from models import Lead, Answer, UserBehavior


def check_database():
    """Check and display all data from the database."""
    print("=" * 60)
    print("📊 LEAD MANAGEMENT DATABASE CHECKER")
    print("=" * 60)

    try:
        db_session = get_db_session()

        # Check Leads table
        print("\n🎯 LEADS DATA:")
        print("-" * 40)
        leads = db_session.query(Lead).all()

        if not leads:
            print("❌ No leads found in database")
        else:
            print(f"✅ Found {len(leads)} lead(s)")

            for i, lead in enumerate(leads, 1):
                print(f"\n📝 LEAD #{i}:")
                print(f"   Session ID: {lead.session_id}")
                print(f"   Name: {lead.name or 'Not provided'}")
                print(f"   Email: {lead.email or 'Not provided'}")
                print(f"   Phone: {lead.phone or 'Not provided'}")
                print(
                    f"   Business Type: {lead.business_type or 'Not provided'}")
                print(f"   Location: {lead.location or 'Not provided'}")
                print(f"   Staff Size: {lead.staff_size or 'Not provided'}")
                print(
                    f"   Monthly Sales: {lead.monthly_sales or 'Not provided'}")

                # Parse features if available
                if lead.features_interested:
                    try:
                        features = json.loads(lead.features_interested)
                        print(
                            f"   Features Interested: {', '.join(features) if features else 'None'}")
                    except:
                        print(
                            f"   Features Interested: {lead.features_interested}")
                else:
                    print(f"   Features Interested: Not provided")

                print(f"   Lead Score: {lead.lead_score or 0}")
                print(f"   Lead Type: {lead.lead_type or 'Unqualified'}")
                print(f"   UTM Source: {lead.utm_source or 'Direct'}")
                print(f"   Created: {lead.created_at}")
                print(f"   Updated: {lead.updated_at}")

        # Check Answers table
        print("\n💬 ANSWERS DATA:")
        print("-" * 40)
        answers = db_session.query(Answer).all()

        if not answers:
            print("❌ No answers found in database")
        else:
            print(f"✅ Found {len(answers)} answer(s)")

            # Group answers by session
            answers_by_session = {}
            for answer in answers:
                if answer.session_id not in answers_by_session:
                    answers_by_session[answer.session_id] = []
                answers_by_session[answer.session_id].append(answer)

            for session_id, session_answers in answers_by_session.items():
                print(f"\n📋 SESSION: {session_id}")
                for answer in session_answers:
                    print(f"   Q{answer.question_id}: {answer.answer_text}")

        # Check User Behavior table
        print("\n👤 USER BEHAVIOR DATA:")
        print("-" * 40)
        behaviors = db_session.query(UserBehavior).all()

        if not behaviors:
            print("❌ No user behavior data found")
        else:
            print(f"✅ Found {len(behaviors)} behavior record(s)")

            for behavior in behaviors:
                print(f"\n🔍 Session: {behavior.session_id}")
                print(f"   Action: {behavior.action_type}")
                print(
                    f"   Data: {behavior.action_data or 'No additional data'}")
                print(f"   Timestamp: {behavior.timestamp}")

        # Summary statistics
        print("\n📈 SUMMARY STATISTICS:")
        print("-" * 40)
        print(f"Total Leads: {len(leads)}")
        print(f"Total Answers: {len(answers)}")
        print(f"Total Behavior Records: {len(behaviors)}")

        if leads:
            sql_leads = len([l for l in leads if l.lead_type == 'SQL'])
            mql_leads = len([l for l in leads if l.lead_type == 'MQL'])
            unqualified = len(
                [l for l in leads if l.lead_type not in ['SQL', 'MQL']])

            print(f"SQL Leads: {sql_leads}")
            print(f"MQL Leads: {mql_leads}")
            print(f"Unqualified Leads: {unqualified}")

            avg_score = sum([l.lead_score or 0 for l in leads]) / len(leads)
            print(f"Average Lead Score: {avg_score:.2f}")

        db_session.close()

    except Exception as e:
        print(f"❌ Error checking database: {str(e)}")

    print("\n" + "=" * 60)


def check_specific_session(session_id):
    """Check data for a specific session ID."""
    print(f"🔍 Checking data for session: {session_id}")
    print("-" * 50)

    try:
        db_session = get_db_session()

        # Get lead data
        lead = db_session.query(Lead).filter_by(session_id=session_id).first()
        if lead:
            print("📝 LEAD DATA:")
            print(f"   Name: {lead.name}")
            print(f"   Email: {lead.email}")
            print(f"   Phone: {lead.phone}")
            print(f"   Score: {lead.lead_score}")
            print(f"   Type: {lead.lead_type}")
        else:
            print("❌ No lead found for this session")

        # Get answers
        answers = db_session.query(Answer).filter_by(
            session_id=session_id).all()
        if answers:
            print(f"\n💬 ANSWERS ({len(answers)}):")
            for answer in answers:
                print(f"   Q{answer.question_id}: {answer.answer_text}")
        else:
            print("\n❌ No answers found for this session")

        # Get behavior data
        behaviors = db_session.query(UserBehavior).filter_by(
            session_id=session_id).all()
        if behaviors:
            print(f"\n👤 BEHAVIOR ({len(behaviors)}):")
            for behavior in behaviors:
                print(f"   {behavior.action_type}: {behavior.action_data}")
        else:
            print("\n❌ No behavior data found for this session")

        db_session.close()

    except Exception as e:
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    print("Choose an option:")
    print("1. Check all database data")
    print("2. Check specific session")
    print("3. Exit")

    while True:
        choice = input("\nEnter your choice (1-3): ").strip()

        if choice == "1":
            check_database()
            break
        elif choice == "2":
            session_id = input("Enter session ID: ").strip()
            if session_id:
                check_specific_session(session_id)
            else:
                print("❌ Please enter a valid session ID")
            break
        elif choice == "3":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.")
