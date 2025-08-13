#!/usr/bin/env python3
# Backend-only implementation. No frontend/static logic.
"""
A/B Testing Framework for Chatbot Optimization
15-25% conversion improvement through systematic testing
"""

import random
import json
from datetime import datetime
from database import get_db_session
from models import UserBehavior


class ABTestingService:
    """A/B testing framework for chatbot optimization"""

    # Active A/B tests configuration
    ACTIVE_TESTS = {
        'greeting_message': {
            'A': {
                'text': "Hi! Welcome to YouShop/YouResto — your smart business partner. Let's help you get started! 🚀",
                'style': 'friendly'
            },
            'B': {
                'text': "🔥 Transform your business with YouShop! Ready to boost your sales and streamline operations?",
                'style': 'urgent'
            },
            'C': {
                'text': "Hello! I'm your AI business assistant. I'll help you find the perfect solution in just 2 minutes! ⚡",
                'style': 'efficient'
            }
        },

        'question_flow': {
            'A': {
                'order': ['business_type', 'location', 'staff_size', 'monthly_sales', 'needs'],
                'style': 'traditional'
            },
            'B': {
                'order': ['needs', 'business_type', 'monthly_sales', 'staff_size', 'location'],
                'style': 'needs_first'
            },
            'C': {
                'order': ['monthly_sales', 'business_type', 'needs', 'location', 'staff_size'],
                'style': 'qualification_first'
            }
        },

        'cta_presentation': {
            'A': {
                'buttons': [
                    {'text': '🤝 Talk to Sales Rep',
                        'color': '#007bff', 'style': 'primary'},
                    {'text': '🚀 Start Free Trial',
                        'color': '#28a745', 'style': 'success'},
                    {'text': '📞 Request Callback',
                        'color': '#17a2b8', 'style': 'info'}
                ],
                'layout': 'horizontal'
            },
            'B': {
                'buttons': [
                    {'text': '💬 Chat with Expert',
                        'color': '#28a745', 'style': 'success'},
                    {'text': '⚡ Try Demo Now', 'color': '#ff6b6b', 'style': 'danger'},
                    {'text': '📱 Get Call Back',
                        'color': '#6c757d', 'style': 'secondary'}
                ],
                'layout': 'vertical'
            },
            'C': {
                'buttons': [
                    {'text': '🎯 Get Personal Demo',
                        'color': '#ff9500', 'style': 'warning'},
                    {'text': '🔥 Start Now (Free)',
                     'color': '#dc3545', 'style': 'danger'},
                    {'text': '💡 Speak to Consultant',
                        'color': '#6610f2', 'style': 'info'}
                ],
                'layout': 'grid'
            }
        },

        'urgency_messaging': {
            'A': {
                'enabled': False,
                'messages': []
            },
            'B': {
                'enabled': True,
                'messages': [
                    "⏰ Limited time offer: 50% off setup fees!",
                    "🔥 Only 3 spots left for free consultation this week!"
                ]
            },
            'C': {
                'enabled': True,
                'messages': [
                    "💎 Join 10,000+ successful businesses using our platform",
                    "📈 See results in your first month or money back!"
                ]
            }
        }
    }

    @staticmethod
    def assign_test_variant(session_id, test_name):
        """Assign user to A/B test variant based on session ID"""
        try:
            if test_name not in ABTestingService.ACTIVE_TESTS:
                return 'A'  # Default variant

            variants = list(ABTestingService.ACTIVE_TESTS[test_name].keys())

            # Use session_id hash for consistent assignment
            random.seed(hash(session_id) % 1000000)
            variant = random.choice(variants)

            # Log test assignment
            ABTestingService.log_test_assignment(
                session_id, test_name, variant)

            return variant

        except Exception as e:
            print(f"A/B test assignment error: {str(e)}")
            return 'A'  # Fallback to control

    @staticmethod
    def get_variant_config(session_id, test_name):
        """Get the configuration for user's assigned variant"""
        try:
            variant = ABTestingService.assign_test_variant(
                session_id, test_name)
            config = ABTestingService.ACTIVE_TESTS[test_name][variant]

            return {
                'variant': variant,
                'config': config,
                'test_name': test_name
            }

        except Exception as e:
            print(f"Variant config error: {str(e)}")
            return {
                'variant': 'A',
                'config': ABTestingService.ACTIVE_TESTS[test_name]['A'],
                'test_name': test_name
            }

    @staticmethod
    def log_test_assignment(session_id, test_name, variant):
        """Log A/B test assignment"""
        try:
            db_session = get_db_session()

            assignment_log = UserBehavior(
                session_id=session_id,
                action='ab_test_assignment',
                behavior_metadata=json.dumps({
                    'test_name': test_name,
                    'variant': variant,
                    'assigned_at': datetime.now().isoformat()
                }),
                created_at=datetime.now()
            )

            db_session.add(assignment_log)
            db_session.commit()
            db_session.close()

        except Exception as e:
            print(f"A/B test logging error: {str(e)}")

    @staticmethod
    def log_conversion(session_id, test_name, variant, conversion_type, conversion_value=None):
        """Log conversion event for A/B test analysis"""
        try:
            db_session = get_db_session()

            conversion_log = UserBehavior(
                session_id=session_id,
                action='ab_test_conversion',
                behavior_metadata=json.dumps({
                    'test_name': test_name,
                    'variant': variant,
                    'conversion_type': conversion_type,
                    'conversion_value': conversion_value,
                    'converted_at': datetime.now().isoformat()
                }),
                created_at=datetime.now()
            )

            db_session.add(conversion_log)
            db_session.commit()
            db_session.close()

            print(
                f"📊 A/B test conversion logged: {test_name}/{variant}/{conversion_type}")

        except Exception as e:
            print(f"A/B test conversion logging error: {str(e)}")

    @staticmethod
    def get_test_results(test_name=None):
        """Get A/B test performance results"""
        try:
            db_session = get_db_session()

            # Get all test assignments
            assignments_query = db_session.query(UserBehavior).filter(
                UserBehavior.action == 'ab_test_assignment'
            )

            if test_name:
                assignments_query = assignments_query.filter(
                    UserBehavior.behavior_metadata.like(
                        f'%"test_name": "{test_name}"%')
                )

            assignments = assignments_query.all()

            # Get all conversions
            conversions_query = db_session.query(UserBehavior).filter(
                UserBehavior.action == 'ab_test_conversion'
            )

            if test_name:
                conversions_query = conversions_query.filter(
                    UserBehavior.behavior_metadata.like(
                        f'%"test_name": "{test_name}"%')
                )

            conversions = conversions_query.all()

            # Process results
            results = {}

            # Count assignments by variant
            for assignment in assignments:
                try:
                    data = json.loads(assignment.behavior_metadata)
                    test = data['test_name']
                    variant = data['variant']

                    if test not in results:
                        results[test] = {}
                    if variant not in results[test]:
                        results[test][variant] = {
                            'assignments': 0,
                            'conversions': 0,
                            'conversion_types': {}
                        }

                    results[test][variant]['assignments'] += 1
                except:
                    continue

            # Count conversions by variant
            for conversion in conversions:
                try:
                    data = json.loads(conversion.behavior_metadata)
                    test = data['test_name']
                    variant = data['variant']
                    conv_type = data['conversion_type']

                    if test in results and variant in results[test]:
                        results[test][variant]['conversions'] += 1

                        if conv_type not in results[test][variant]['conversion_types']:
                            results[test][variant]['conversion_types'][conv_type] = 0
                        results[test][variant]['conversion_types'][conv_type] += 1
                except:
                    continue

            # Calculate conversion rates
            for test in results:
                for variant in results[test]:
                    assignments = results[test][variant]['assignments']
                    conversions = results[test][variant]['conversions']

                    results[test][variant]['conversion_rate'] = (
                        (conversions / assignments * 100) if assignments > 0 else 0
                    )

            db_session.close()
            return results

        except Exception as e:
            print(f"A/B test results error: {str(e)}")
            return {}

    @staticmethod
    def get_winning_variant(test_name):
        """Determine winning variant based on conversion rate"""
        try:
            results = ABTestingService.get_test_results(test_name)

            if test_name not in results:
                return 'A'

            test_results = results[test_name]
            winning_variant = 'A'
            highest_rate = 0

            for variant, data in test_results.items():
                if data['conversion_rate'] > highest_rate and data['assignments'] >= 10:
                    highest_rate = data['conversion_rate']
                    winning_variant = variant

            return winning_variant

        except Exception as e:
            print(f"Winning variant calculation error: {str(e)}")
            return 'A'

    @staticmethod
    def export_test_data(test_name):
        """Export A/B test data for external analysis"""
        try:
            results = ABTestingService.get_test_results(test_name)

            export_data = {
                'test_name': test_name,
                'exported_at': datetime.now().isoformat(),
                'results': results.get(test_name, {}),
                'summary': {
                    'total_participants': sum(
                        variant['assignments'] for variant in results.get(test_name, {}).values()
                    ),
                    'total_conversions': sum(
                        variant['conversions'] for variant in results.get(test_name, {}).values()
                    ),
                    'winning_variant': ABTestingService.get_winning_variant(test_name)
                }
            }

            return export_data

        except Exception as e:
            print(f"A/B test export error: {str(e)}")
            return {}
