# Backend-only workflow configuration. No frontend/static logic.
# Workflow Configuration
WORKFLOW_CONFIG = {
    "scoring": {
        "session_opened": 5,
        "replied_to_greeting": 5,
        "answered_question": 5,
        "answered_all_questions": 10,
        "shared_contact": 10,
        "clicked_product": 5,
        "clicked_pricing": 10,
        "clicked_demo": 15,
        "meaningful_reply": 10,
        "quick_reply": 5,  # < 2 minutes
        "detailed_answer": 5,  # > 10 characters
        "cta_clicked": 15,
        "early_dropout": -10,
        "ignored_cta": 0,
        "completed_journey": 10
    },

    "lead_thresholds": {
        "sql": 60,  # Sales Qualified Lead
        "mql": 30,  # Marketing Qualified Lead
        "unqualified": 0
    },

    "questions_workflow": [
        {
            "id": 1,
            "step": "greeting",
            "question_text": "Hi! Welcome to YouShop/YouResto — your smart business partner. Let's help you get started 🚀\n\nCan I ask a few quick questions to customize your solution?",
            "question_type": "single_choice",
            "options": ["Yes, go ahead", "What is this about?", "No thanks"],
            "base_score": 5,
            "required": True,
            "order_index": 1
        },
        {
            "id": 2,
            "step": "profile",
            "question_text": "What type of business do you run?",
            "question_type": "single_choice",
            "options": ["Kirana / Retail Shop", "Restaurant / Café", "Wholesale / FMCG", "Other"],
            "base_score": 5,
            "required": True,
            "order_index": 2
        },
        {
            "id": 3,
            "step": "profile",
            "question_text": "Where is your shop located?",
            "question_type": "text",
            "options": None,
            "base_score": 5,
            "required": True,
            "order_index": 3
        },
        {
            "id": 4,
            "step": "profile",
            "question_text": "How many staff members work with you?",
            "question_type": "single_choice",
            "options": ["Just me", "2–5", "6–15", "More than 15"],
            "base_score": 5,
            "required": True,
            "order_index": 4
        },
        {
            "id": 5,
            "step": "profile",
            "question_text": "What's your monthly sales volume? (approx.)",
            "question_type": "single_choice",
            "options": ["Less than ₹50K", "₹50K – ₹2L", "₹2L – ₹5L", "₹5L+"],
            "base_score": 5,
            "required": True,
            "order_index": 5
        },
        {
            "id": 6,
            "step": "profile",
            "question_text": "What do you need help with?",
            "question_type": "multiple_choice",
            "options": ["Billing / Invoicing", "QR Payments", "Staff/HR", "Inventory", "Online Store", "WhatsApp Marketing", "Loans"],
            "base_score": 5,
            "required": True,
            "order_index": 6
        },
        {
            "id": 7,
            "step": "contact",
            "question_text": "Can we get your contact details to send your custom setup or offers?",
            "question_type": "contact_form",
            "options": ["Share Phone", "Share Email", "Skip for now"],
            "base_score": 10,
            "required": False,
            "order_index": 7
        }
    ],

    "product_menu": [
        {"id": "billing", "title": "📊 Billing & Invoicing",
            "description": "GST-compliant billing and invoicing", "score": 5},
        {"id": "inventory", "title": "📦 Inventory",
            "description": "Track and manage your stock", "score": 5},
        {"id": "qr_payments", "title": "💳 QR / Payments",
            "description": "Accept digital payments easily", "score": 5},
        {"id": "staff_hr", "title": "👥 Staff & HR",
            "description": "Manage your team efficiently", "score": 5},
        {"id": "online_selling", "title": "🛒 Online Selling",
            "description": "Sell online and reach more customers", "score": 5},
        {"id": "whatsapp_tools", "title": "💬 WhatsApp Tools",
            "description": "Business communication tools", "score": 5},
        {"id": "loans_offers", "title": "💰 Loans & Offers",
            "description": "Financial solutions for your business", "score": 5},
        {"id": "demo", "title": "🎥 Watch Demo",
            "description": "See our products in action", "score": 15},
        {"id": "other", "title": "❓ Other Questions",
            "description": "Get help with anything else", "score": 5}
    ],

    "cta_options": [
        {"id": "talk_to_sales", "title": "🤝 Talk to Sales Rep",
            "description": "Connect with our sales team", "score": 15},
        {"id": "request_callback", "title": "📞 Request Callback",
            "description": "We'll call you back", "score": 15},
        {"id": "start_trial", "title": "🚀 Start Free Trial",
            "description": "Try our products for free", "score": 15},
        {"id": "restart_bot", "title": "🔄 Restart Bot",
            "description": "Start the conversation over", "score": 0},
        {"id": "human_help", "title": "❓ Need Human Help",
            "description": "Connect with our support team", "score": 10}
    ]
}

# Feature-specific FAQs
FEATURE_FAQS = {
    "billing": {
        "title": "Our billing app is GST-compliant, works offline, supports barcodes & invoices.",
        "faqs": [
            "How does it work?",
            "What devices does it support?",
            "Can I print invoices?",
            "Can I try a demo?"
        ]
    },
    "qr_payments": {
        "title": "Accept payments via UPI, card, QR, wallets, and track them easily.",
        "faqs": [
            "How do I get my QR?",
            "How do settlements work?",
            "Is it free to use?"
        ]
    },
    "whatsapp_tools": {
        "title": "Use WhatsApp to send invoices, take orders, or run promotions.",
        "faqs": [
            "How does WhatsApp Ordering work?",
            "Can I send bulk messages?",
            "How much does this cost?"
        ]
    }
}
