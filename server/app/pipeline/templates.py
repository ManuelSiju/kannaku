"""Code-written lines (no LLM) in English, Malayalam and Hindi.

Alfii's opener, budget notes, next steps, claim corrections, scam and out-of-scope replies, verdict fallbacks, short
answers and suggested follow-ups. Malayalam and Hindi text should be reviewed by a native speaker.
"""

from __future__ import annotations

LANGS = ("en", "ml", "hi")
LANG_NAMES = {"en": "English", "ml": "Malayalam", "hi": "Hindi"}

NAMES = {
    "en": {"alfii": "Alfii", "sankz": "Sankz", "dani": "Dani", "vick": "Vick"},
    "ml": {"alfii": "ആൽഫി", "sankz": "സാങ്ക്സ്", "dani": "ഡാനി", "vick": "വിക്ക്"},
    "hi": {"alfii": "अल्फ़ी", "sankz": "सैंक्स", "dani": "डैनी", "vick": "विक"},
}

T: dict[str, dict[str, str]] = {
    "en": {
        "opener": "Let me ask {names}.",
        "opener_one": "Let me ask {names}.",
        "opener_none": "Let me look at this.",
        "and": " and ",
        "budget_note": "{agent} has left a note about your budget on your screen.",
        "claim": 'You were told "{claim}", but {source} says "{evidence}".',
        "claim_source_doc": "the paper",
        "claim_source_brochure": "the brochure",
        "claim_cant_check": 'You were told "{claim}". I cannot check that, so please do not rely on it.',
        "next_wait": "Please wait a day before you sign anything.",
        "next_guardian": "Talk to {guardian} before you decide.",
        "next_ask": 'Before you decide, ask: "{question}"',
        "next_paper": "Show me the paper they gave you.",
        "red": "My advice: do not go ahead with this as it is.",
        "yellow": "Be careful: get clear answers before you decide.",
        "green": "This looks reasonable for your family, but take your time.",
        "short_red": "Please don't go ahead with this as it is.",
        "short_yellow": "Be careful; get clear answers before you decide.",
        "short_green": "This looks reasonable, but take your time.",
        "scam_right": "You did the right thing by asking me.",
        "scam_action": "Please don't share any code or pay anyone. Hang up and call your bank yourself.",
        "scam_generic": "This looks like a trick to take your money.",
        "out_of_scope": "I can only help with money questions. You could ask me one of these.",
        "clarify": "Is this about a loan, a policy, an investment or a payment?",
        "note_premium_savings": "This premium is {premium_share_of_savings} of your savings each year.",
        "note_premium_income": "Each month this premium is {premium_share_of_income} of your income.",
        "note_surplus": "After this, you would have {surplus_after} left each month.",
        "note_buffer": "Your savings would cover {buffer_months_after} of costs.",
        "note_emi": "Your EMIs would take {emi_share} of your income.",
        "note_invest_savings": "This amount is {invest_share_of_savings} of your savings.",
    },
    "ml": {
        "opener": "ഞാൻ {names} എന്നിവരോട് ചോദിക്കട്ടെ.",
        "opener_one": "ഞാൻ {names}-നോട് ചോദിക്കട്ടെ.",
        "opener_none": "ഞാൻ ഇതൊന്ന് നോക്കട്ടെ.",
        "and": ", ",
        "budget_note": "{agent} നിങ്ങളുടെ ബജറ്റിനെക്കുറിച്ച് ഒരു കുറിപ്പ് സ്ക്രീനിൽ വെച്ചിട്ടുണ്ട്.",
        "claim": 'നിങ്ങളോട് "{claim}" എന്ന് പറഞ്ഞു, പക്ഷേ {source} പറയുന്നത് "{evidence}" എന്നാണ്.',
        "claim_source_doc": "കടലാസിൽ",
        "claim_source_brochure": "ബ്രോഷറിൽ",
        "claim_cant_check": 'നിങ്ങളോട് "{claim}" എന്ന് പറഞ്ഞു. എനിക്കത് പരിശോധിക്കാൻ കഴിയില്ല, അതിനാൽ അതിൽ വിശ്വസിക്കരുത്.',
        "next_wait": "ഒപ്പിടുന്നതിന് മുമ്പ് ഒരു ദിവസം കാത്തിരിക്കൂ.",
        "next_guardian": "തീരുമാനിക്കുന്നതിന് മുമ്പ് {guardian}-നോട് സംസാരിക്കൂ.",
        "next_ask": 'തീരുമാനിക്കുന്നതിന് മുമ്പ് ചോദിക്കൂ: "{question}"',
        "next_paper": "അവർ തന്ന കടലാസ് എന്നെ കാണിക്കൂ.",
        "red": "എന്റെ ഉപദേശം: ഇത് ഇപ്പോഴത്തെ രൂപത്തിൽ മുന്നോട്ട് കൊണ്ടുപോകരുത്.",
        "yellow": "ശ്രദ്ധിക്കൂ: തീരുമാനിക്കുന്നതിന് മുമ്പ് വ്യക്തമായ ഉത്തരങ്ങൾ വാങ്ങൂ.",
        "green": "ഇത് നിങ്ങളുടെ കുടുംബത്തിന് ന്യായമാണെന്ന് തോന്നുന്നു, എങ്കിലും സമയമെടുക്കൂ.",
        "short_red": "ഇത് ഇപ്പോഴത്തെ രൂപത്തിൽ ചെയ്യരുത്.",
        "short_yellow": "ശ്രദ്ധിക്കൂ; തീരുമാനിക്കുന്നതിന് മുമ്പ് വ്യക്തമായ ഉത്തരങ്ങൾ വാങ്ങൂ.",
        "short_green": "ഇത് ന്യായമാണെന്ന് തോന്നുന്നു, എങ്കിലും സമയമെടുക്കൂ.",
        "scam_right": "എന്നോട് ചോദിച്ചത് വളരെ നന്നായി.",
        "scam_action": "ഒരു കോഡും പറഞ്ഞുകൊടുക്കരുത്, ആർക്കും പണം അയക്കരുത്. ഫോൺ വെച്ച് നിങ്ങളുടെ ബാങ്കിനെ നേരിട്ട് വിളിക്കൂ.",
        "scam_generic": "ഇത് നിങ്ങളുടെ പണം തട്ടാനുള്ള ഒരു തന്ത്രമായി തോന്നുന്നു.",
        "out_of_scope": "പണത്തെക്കുറിച്ചുള്ള ചോദ്യങ്ങളിൽ മാത്രമേ എനിക്ക് സഹായിക്കാനാകൂ. ഇവയിൽ ഒന്ന് ചോദിക്കാം.",
        "clarify": "ഇത് ഒരു ലോണിനെക്കുറിച്ചാണോ, പോളിസിയാണോ, നിക്ഷേപമാണോ, അതോ ഒരു പണമിടപാടാണോ?",
        "note_premium_savings": "ഈ പ്രീമിയം ഓരോ വർഷവും നിങ്ങളുടെ സമ്പാദ്യത്തിന്റെ {premium_share_of_savings} ആണ്.",
        "note_premium_income": "ഓരോ മാസവും ഈ പ്രീമിയം നിങ്ങളുടെ വരുമാനത്തിന്റെ {premium_share_of_income} ആണ്.",
        "note_surplus": "ഇതിനുശേഷം ഓരോ മാസവും {surplus_after} ബാക്കിയുണ്ടാകും.",
        "note_buffer": "നിങ്ങളുടെ സമ്പാദ്യം {buffer_months_after} ചെലവിന് തികയും.",
        "note_emi": "EMI-കൾ നിങ്ങളുടെ വരുമാനത്തിന്റെ {emi_share} എടുക്കും.",
        "note_invest_savings": "ഈ തുക നിങ്ങളുടെ സമ്പാദ്യത്തിന്റെ {invest_share_of_savings} ആണ്.",
    },
    "hi": {
        "opener": "चलिए, {names} से पूछते हैं।",
        "opener_one": "चलिए, {names} से पूछते हैं।",
        "opener_none": "चलिए, इसे देखते हैं।",
        "and": " और ",
        "budget_note": "{agent} ने आपके बजट के बारे में स्क्रीन पर एक नोट छोड़ा है।",
        "claim": 'आपसे कहा गया "{claim}", लेकिन {source} में लिखा है "{evidence}"।',
        "claim_source_doc": "कागज़",
        "claim_source_brochure": "ब्रोशर",
        "claim_cant_check": 'आपसे कहा गया "{claim}"। मैं इसकी जाँच नहीं कर सकती, इसलिए इस पर भरोसा न करें।',
        "next_wait": "कुछ भी साइन करने से पहले एक दिन रुकिए।",
        "next_guardian": "फ़ैसला करने से पहले {guardian} से बात कीजिए।",
        "next_ask": 'फ़ैसला करने से पहले पूछिए: "{question}"',
        "next_paper": "उन्होंने जो कागज़ दिया है, वह मुझे दिखाइए।",
        "red": "मेरी सलाह: इसे ऐसे ही आगे मत बढ़ाइए।",
        "yellow": "सावधान रहिए: फ़ैसले से पहले साफ़ जवाब लीजिए।",
        "green": "यह आपके परिवार के लिए ठीक लगता है, फिर भी समय लीजिए।",
        "short_red": "कृपया इसे ऐसे ही आगे मत बढ़ाइए।",
        "short_yellow": "सावधान रहिए; फ़ैसले से पहले साफ़ जवाब लीजिए।",
        "short_green": "यह ठीक लगता है, फिर भी समय लीजिए।",
        "scam_right": "आपने मुझसे पूछकर बिल्कुल सही किया।",
        "scam_action": "कोई भी कोड मत बताइए, किसी को पैसे मत भेजिए। फ़ोन रखकर ख़ुद अपने बैंक को फ़ोन कीजिए।",
        "scam_generic": "यह आपके पैसे ठगने की चाल लगती है।",
        "out_of_scope": "मैं सिर्फ़ पैसों से जुड़े सवालों में मदद कर सकती हूँ। आप इनमें से कुछ पूछ सकते हैं।",
        "clarify": "क्या यह लोन, पॉलिसी, निवेश या किसी भुगतान के बारे में है?",
        "note_premium_savings": "यह प्रीमियम हर साल आपकी बचत का {premium_share_of_savings} है।",
        "note_premium_income": "हर महीने यह प्रीमियम आपकी आय का {premium_share_of_income} है।",
        "note_surplus": "इसके बाद हर महीने {surplus_after} बचेंगे।",
        "note_buffer": "आपकी बचत {buffer_months_after} के ख़र्च के लिए काफ़ी है।",
        "note_emi": "आपकी EMI आपकी आय का {emi_share} लेगी।",
        "note_invest_savings": "यह रकम आपकी बचत का {invest_share_of_savings} है।",
    },
}

# Short scam explanations, one per rule (the fast path says at most one of them).
SCAM_SHORT: dict[str, dict[str, str]] = {
    "en": {
        "otp_pin_request": "No real bank ever asks for your OTP or PIN.",
        "remote_access": "Never install an app that lets a stranger see your phone.",
        "digital_arrest": "Police never arrest anyone or ask for money on a video call.",
        "kyc_urgency": "Banks do not block accounts over a phone call about KYC.",
        "pay_to_receive": "You never have to pay money to receive money.",
        "collect_request": "Approving a request or entering your PIN sends money out, not in.",
    },
    "ml": {
        "otp_pin_request": "ഒരു യഥാർത്ഥ ബാങ്കും നിങ്ങളുടെ OTP-യോ PIN-ഓ ചോദിക്കില്ല.",
        "remote_access": "അപരിചിതന് നിങ്ങളുടെ ഫോൺ കാണാൻ കഴിയുന്ന ആപ്പ് ഒരിക്കലും ഇടരുത്.",
        "digital_arrest": "പോലീസ് വീഡിയോ കോളിൽ ആരെയും അറസ്റ്റ് ചെയ്യുകയോ പണം ചോദിക്കുകയോ ഇല്ല.",
        "kyc_urgency": "KYC-യുടെ പേരിൽ ഫോൺ വിളിച്ച് ബാങ്കുകൾ അക്കൗണ്ട് ബ്ലോക്ക് ചെയ്യാറില്ല.",
        "pay_to_receive": "പണം കിട്ടാൻ വേണ്ടി ഒരിക്കലും പണം അടയ്ക്കേണ്ടതില്ല.",
        "collect_request": "റിക്വസ്റ്റ് അംഗീകരിക്കുകയോ PIN അടിക്കുകയോ ചെയ്താൽ പണം പോകും, വരില്ല.",
    },
    "hi": {
        "otp_pin_request": "कोई भी असली बैंक आपका OTP या PIN नहीं माँगता।",
        "remote_access": "कोई ऐसा ऐप कभी मत डालिए जिससे अजनबी आपका फ़ोन देख सके।",
        "digital_arrest": "पुलिस वीडियो कॉल पर न किसी को गिरफ़्तार करती है, न पैसे माँगती है।",
        "kyc_urgency": "बैंक KYC के नाम पर फ़ोन करके खाता बंद नहीं करते।",
        "pay_to_receive": "पैसे पाने के लिए कभी पैसे नहीं देने पड़ते।",
        "collect_request": "रिक्वेस्ट मानने या PIN डालने से पैसे जाते हैं, आते नहीं।",
    },
}

# Suggested follow-ups (tappable). Each maps to a question the pipeline can answer from facts it already computes.
FOLLOWUPS: dict[str, dict[str, list[str]]] = {
    "en": {
        "insurance_offer": [
            "What would an FD give me instead?",
            "How much of this is guaranteed?",
            "Can I afford this premium?",
        ],
        "loan_offer": ["What is the real interest rate?", "What would my EMI be?", "Can I afford this EMI?"],
        "stock_tip": ["What are the warning signs?", "How much of my savings is this?"],
        "sip_or_fund_question": ["What could this grow to?", "Can I afford this every month?"],
        "general_money": ["What would an FD give me?"],
        "scam_or_payment_request": ["Is this message real?"],
        "out_of_scope": ["Is this insurance plan good for me?", "Should I take this loan?", "Is this stock tip safe?"],
    },
    "ml": {
        "insurance_offer": ["പകരം FD-യിൽ എത്ര കിട്ടും?", "ഇതിൽ എത്ര ഉറപ്പാണ്?", "ഈ പ്രീമിയം എനിക്ക് താങ്ങാനാകുമോ?"],
        "loan_offer": ["യഥാർത്ഥ പലിശ എത്രയാണ്?", "എന്റെ EMI എത്രയാകും?", "ഈ EMI എനിക്ക് താങ്ങാനാകുമോ?"],
        "stock_tip": ["എന്തൊക്കെയാണ് അപകട സൂചനകൾ?", "ഇത് എന്റെ സമ്പാദ്യത്തിന്റെ എത്ര ഭാഗമാണ്?"],
        "sip_or_fund_question": ["ഇത് എത്രയായി വളരാം?", "എല്ലാ മാസവും ഇത് എനിക്ക് താങ്ങാനാകുമോ?"],
        "general_money": ["FD-യിൽ എത്ര കിട്ടും?"],
        "scam_or_payment_request": ["ഈ സന്ദേശം സത്യമാണോ?"],
        "out_of_scope": ["ഈ ഇൻഷുറൻസ് പ്ലാൻ എനിക്ക് നല്ലതാണോ?", "ഈ ലോൺ എടുക്കണോ?", "ഈ ഷെയർ ടിപ്പ് സുരക്ഷിതമാണോ?"],
    },
    "hi": {
        "insurance_offer": ["इसके बदले FD में कितना मिलेगा?", "इसमें कितना पक्का है?", "क्या मैं यह प्रीमियम भर पाऊँगी?"],
        "loan_offer": ["असली ब्याज दर कितनी है?", "मेरी EMI कितनी होगी?", "क्या मैं यह EMI भर पाऊँगी?"],
        "stock_tip": ["ख़तरे के संकेत क्या हैं?", "यह मेरी बचत का कितना हिस्सा है?"],
        "sip_or_fund_question": ["यह कितना बढ़ सकता है?", "क्या मैं हर महीने यह भर पाऊँगी?"],
        "general_money": ["FD में कितना मिलेगा?"],
        "scam_or_payment_request": ["क्या यह संदेश असली है?"],
        "out_of_scope": ["क्या यह बीमा प्लान मेरे लिए ठीक है?", "क्या मुझे यह लोन लेना चाहिए?", "क्या यह शेयर टिप सुरक्षित है?"],
    },
}


def lang_of(code: str | None) -> str:
    return code if code in LANGS else "en"


def t(lang: str, key: str, **kw: str) -> str:
    return T[lang_of(lang)][key].format(**kw)


def name(lang: str, agent: str) -> str:
    return NAMES[lang_of(lang)].get(agent, agent)


def opener(agents: list[str], lang: str = "en") -> str:
    names = [name(lang, a) for a in agents]
    if not names:
        return t(lang, "opener_none")
    sep = T[lang_of(lang)]["and"]
    if len(names) == 1:
        return t(lang, "opener_one", names=names[0])
    return t(lang, "opener", names=", ".join(names[:-1]) + sep + names[-1])


def followups(case_type: str, lang: str = "en") -> list[str]:
    table = FOLLOWUPS[lang_of(lang)]
    return list(table.get(case_type, table["general_money"]))[:3]


# On-screen personal notes (code-written; never spoken in discreet mode). Placeholders filled with screen values.
NOTES: dict[str, list[tuple[str, str]]] = {
    "insurance_offer": [
        ("note_premium_savings", "premium_share_of_savings"),
        ("note_premium_income", "premium_share_of_income"),
        ("note_surplus", "surplus_after"),
        ("note_buffer", "buffer_months_after"),
    ],
    "loan_offer": [
        ("note_emi", "emi_share"),
        ("note_surplus", "surplus_after"),
        ("note_buffer", "buffer_months_after"),
    ],
    "stock_tip": [("note_invest_savings", "invest_share_of_savings")],
    "sip_or_fund_question": [("note_surplus", "surplus_after"), ("note_buffer", "buffer_months_after")],
}
NOTES["ulip"] = NOTES["insurance_offer"]
NOTES["shares"] = NOTES["ipo"] = NOTES["stock_tip"]
