import json
from datetime import datetime
from models import Question, Answer, Lead, UserBehavior
from database import get_db_session
from workflow_config import WORKFLOW_CONFIG


class QuestionService:
    @staticmethod
    def get_questions():
        """Fetch predefined questions from configuration."""
        return WORKFLOW_CONFIG['questions_workflow']


class AnswerService:
    @staticmethod
    def log_answer(session_id, question_id, answer_text, time_taken=None):
        """Log a single answer to the database."""
        db_session = get_db_session()
        try:
            # Calculate score for this answer
            score = ScoringService.calculate_answer_score(
                question_id, answer_text, time_taken)

            new_answer = Answer(
                session_id=session_id,
                question_id=question_id,
                answer_text=answer_text,
                time_taken=time_taken,
                score_earned=score
            )
            db_session.add(new_answer)

            # Update lead total score
            LeadService.update_lead_score(session_id, score)

            db_session.commit()
            return True, score
        except Exception as e:
            print(f"Error logging answer: {e}")
            db_session.rollback()
            return False, 0
        finally:
            db_session.close()


class ScoringService:
    @staticmethod
    def get_scoring_map():
        """Get scoring configuration."""
        return WORKFLOW_CONFIG['scoring']

    @staticmethod
    def get_lead_thresholds():
        """Get lead qualification thresholds."""
        return WORKFLOW_CONFIG['lead_thresholds']

    @staticmethod
    def calculate_answer_score(question_id, answer_text, time_taken=None):
        """Calculate score for a specific answer."""
        scoring_map = ScoringService.get_scoring_map()
        base_score = 5  # Default base score
        bonus_score = 0

        # Bonus for detailed answers (> 10 characters for text fields)
        if len(answer_text.strip()) > 10:
            bonus_score += scoring_map['detailed_answer']

        # Bonus for quick replies (< 120 seconds)
        if time_taken and time_taken < 120:
            bonus_score += scoring_map['quick_reply']

        return base_score + bonus_score

    @staticmethod
    def log_behavior(session_id, action, metadata=None):
        """Log user behavior and return score change."""
        db_session = get_db_session()
        try:
            scoring_map = ScoringService.get_scoring_map()
            score_change = scoring_map.get(action, 0)

            behavior = UserBehavior(
                session_id=session_id,
                action=action,
                score_change=score_change,
                behavior_metadata=json.dumps(metadata) if metadata else None
            )
            db_session.add(behavior)

            # Update lead total score
            LeadService.update_lead_score(session_id, score_change)

            db_session.commit()
            return score_change
        except Exception as e:
            print(f"Error logging behavior: {e}")
            db_session.rollback()
            return 0
        finally:
            db_session.close()

    @staticmethod
    def calculate_lead_type(total_score):
        """Determine lead type based on total score."""
        thresholds = ScoringService.get_lead_thresholds()
        if total_score >= thresholds['sql']:
            return "SQL"  # Sales Qualified Lead
        elif total_score >= thresholds['mql']:
            return "MQL"  # Marketing Qualified Lead
        else:
            return "Unqualified"


class LeadService:
    @staticmethod
    def create_lead(session_id, utm_source=None):
        """Create a new lead session."""
        db_session = get_db_session()
        try:
            lead = Lead(
                session_id=session_id,
                utm_source=utm_source,
                lead_score=0
            )
            db_session.add(lead)
            db_session.commit()

            # Log session opened behavior
            ScoringService.log_behavior(session_id, 'session_opened')

            return True
        except Exception as e:
            print(f"Error creating lead: {e}")
            db_session.rollback()
            return False
        finally:
            db_session.close()

    @staticmethod
    def update_lead_score(session_id, score_change):
        """Update lead total score."""
        db_session = get_db_session()
        try:
            lead = db_session.query(Lead).filter_by(
                session_id=session_id).first()
            if lead:
                lead.lead_score += score_change
                lead.lead_type = ScoringService.calculate_lead_type(
                    lead.lead_score)
                db_session.commit()
        except Exception as e:
            print(f"Error updating lead score: {e}")
            db_session.rollback()
        finally:
            db_session.close()

    @staticmethod
    def update_lead_profile(session_id, profile_data):
        """Update lead profile information."""
        db_session = get_db_session()
        try:
            lead = db_session.query(Lead).filter_by(
                session_id=session_id).first()
            if lead:
                # Update lead attributes from profile data
                for key, value in profile_data.items():
                    if hasattr(lead, key):
                        if key == 'features_interested' and isinstance(value, list):
                            setattr(lead, key, json.dumps(value))
                        else:
                            setattr(lead, key, value)
                db_session.commit()
                return True
            return False
        except Exception as e:
            print(f"Error updating lead profile: {e}")
            db_session.rollback()
            return False
        finally:
            db_session.close()

    @staticmethod
    def get_lead_summary(session_id):
        """Get complete lead summary for CRM export."""
        db_session = get_db_session()
        try:
            lead = db_session.query(Lead).filter_by(
                session_id=session_id).first()
            if lead:
                # Calculate lead type based on current score
                lead_type = ScoringService.calculate_lead_type(lead.lead_score)

                # Update lead type in database
                lead.lead_type = lead_type
                db_session.commit()

                return {
                    'session_id': lead.session_id,
                    'name': lead.name,
                    'location': lead.location,
                    'business_type': lead.business_type,
                    'staff_size': lead.staff_size,
                    'monthly_sales': lead.monthly_sales,
                    'features_interested': json.loads(lead.features_interested) if lead.features_interested else [],
                    'contact_info': lead.phone or lead.email,
                    'email': lead.email,
                    'phone': lead.phone,
                    'lead_score': lead.lead_score,
                    'lead_type': lead_type,
                    'utm_source': lead.utm_source,
                    'created_at': lead.created_at.isoformat() if lead.created_at else None,
                    'updated_at': lead.updated_at.isoformat() if lead.updated_at else None
                }
            return None
        except Exception as e:
            print(f"Error getting lead summary: {e}")
            return None
        finally:
            db_session.close()

    @staticmethod
    def check_all_questions_answered(session_id):
        """Check if all required questions have been answered."""
        db_session = get_db_session()
        try:
            # Get all required questions
            questions = QuestionService.get_questions()
            required_questions = [q['id']
                                  for q in questions if q.get('required', True)]

            # Get answered questions for this session
            answered_questions = db_session.query(Answer.question_id).filter_by(
                session_id=session_id).distinct().all()
            answered_question_ids = [row[0] for row in answered_questions]

            # Check if all required questions are answered
            all_answered = all(
                qid in answered_question_ids for qid in required_questions)

            if all_answered:
                # Award bonus for completing all questions
                ScoringService.log_behavior(
                    session_id, 'answered_all_questions')

            return all_answered
        except Exception as e:
            print(f"Error checking questions completion: {e}")
            return False
        finally:
            db_session.close()
