#!/usr/bin/env python3
"""
Test 15 different 10-turn conversations in English to identify 
potential language detection false positives
"""

import re
import json

def test_phrase_detection_logic(query):
    """Simulate the frontend phrase detection logic"""
    
    # All language phrases from frontend
    common_phrases_by_language = {
        'es': ['hola', 'gracias', 'hasta luego', 'hasta la vista', 'buenas noches', 'buenos días', 'buenas tardes', 'por favor', 'de nada', 'lo siento', 'perdón', 'disculpe', 'ya me voy', 'nos vemos', 'adiós', 'chao', 'cómo estás', 'como estas', 'qué tal', 'que tal', 'muy bien', 'está bien', 'esta bien'],
        'fr': ['bonjour', 'salut', 'merci', 'au revoir', 'à bientôt', 'bonne nuit', 'bonne soirée', 's\'il vous plaît', 'de rien', 'désolé', 'pardon', 'excusez-moi', 'comment allez-vous', 'comment ça va', 'ça va', 'très bien', 'ça marche'],
        'de': ['hallo', 'guten tag', 'danke', 'auf wiedersehen', 'tschüss', 'gute nacht', 'bitte', 'entschuldigung', 'wie geht es dir', 'wie gehts', 'gut', 'sehr gut'],
        'it': ['ciao', 'buongiorno', 'grazie', 'arrivederci', 'buonanotte', 'prego', 'scusa', 'come stai', 'come va', 'bene', 'molto bene'],
        'pt': ['olá', 'oi', 'obrigado', 'obrigada', 'tchau', 'até logo', 'boa noite', 'por favor', 'desculpa', 'como está', 'como vai', 'bem', 'muito bem'],
        'zh': ['你好', '谢谢', '再见', '晚安', '请', '对不起', '你怎么样', '很好'],
        'ja': ['こんにちは', 'ありがとう', 'さようなら', 'すみません', 'お元気ですか', 'はい'],
        'ko': ['안녕하세요', '감사합니다', '안녕히 가세요', '죄송합니다', '어떻게 지내세요', '좋습니다'],
        'ru': ['привет', 'спасибо', 'до свидания', 'пожалуйста', 'извините', 'как дела', 'хорошо'],
        'ar': ['مرحبا', 'شكرا', 'مع السلامة', 'من فضلك', 'آسف', 'كيف حالك', 'بخير'],
        'hi': ['नमस्ते', 'धन्यवाद', 'अलविदा', 'कृपया', 'माफ करें', 'आप कैसे हैं', 'अच्छा'],
        'nl': ['hallo', 'dank je', 'tot ziens', 'alsjeblieft', 'sorry', 'hoe gaat het', 'goed'],
        'sv': ['hej', 'tack', 'hej då', 'tack så mycket', 'ursäkta', 'hur mår du', 'bra'],
        'da': ['hej', 'tak', 'farvel', 'undskyld', 'hvordan har du det', 'godt'],
        'no': ['hei', 'takk', 'ha det', 'unnskyld', 'hvordan har du det', 'bra'],
        'fi': ['hei', 'kiitos', 'näkemiin', 'anteeksi', 'mitä kuuluu', 'hyvää'],
        'pl': ['cześć', 'dziękuję', 'do widzenia', 'przepraszam', 'jak się masz', 'dobrze'],
        'tr': ['merhaba', 'teşekkürler', 'güle güle', 'özür dilerim', 'nasılsın', 'iyi'],
        'he': ['שלום', 'תודה', 'להתראות', 'סליחה', 'איך אתה', 'טוב'],
        'th': ['สวัสดี', 'ขอบคุณ', 'ลาก่อน', 'ขอโทษ', 'สบายดีไหม', 'ดี'],
        'vi': ['xin chào', 'cảm ơn', 'tạm biệt', 'xin lỗi', 'bạn khỏe không', 'tốt'],
        'uk': ['привіт', 'дякую', 'до побачення', 'вибачте', 'як справи', 'добре'],
        'bg': ['здравей', 'благодаря', 'довиждане', 'извинете', 'как сте', 'добре'],
        'cs': ['ahoj', 'děkuji', 'na shledanou', 'promiňte', 'jak se máte', 'dobře'],
        'sk': ['ahoj', 'ďakujem', 'dovidenia', 'prepáčte', 'ako sa máte', 'dobre'],
        'hr': ['bok', 'hvala', 'doviđenja', 'oprostite', 'kako ste', 'dobro'],
        'sr': ['здраво', 'хвала', 'довиђења', 'извините', 'како сте', 'добро'],
        'sl': ['zdravo', 'hvala', 'nasvidenje', 'oprostite', 'kako ste', 'dobro'],
        'ro': ['salut', 'mulțumesc', 'la revedere', 'scuzați-mă', 'ce mai faceți', 'bine'],
        'hu': ['szia', 'köszönöm', 'viszlát', 'elnézést', 'hogy vagy', 'jól']
    }
    
    query_lower = query.lower()
    detected_language = None
    confidence = 0
    matched_phrases = []
    
    # Apply the fixed logic with word boundaries
    for lang_code, phrases in common_phrases_by_language.items():
        lang_matches = []
        for phrase in phrases:
            # Use word boundaries to avoid matching 'oi' in 'doing' or 'por' in 'important'
            regex = re.compile(f"\\b{re.escape(phrase)}\\b", re.IGNORECASE)
            if regex.search(query_lower):
                lang_matches.append(phrase)
        
        if lang_matches:
            # Require multiple phrase matches OR longer phrases for higher confidence
            has_multiple_matches = len(lang_matches) > 1
            has_long_phrase = any(len(phrase) > 4 for phrase in lang_matches)
            lang_confidence = 0.9 if (has_multiple_matches or has_long_phrase) else 0.6
            
            if lang_confidence > confidence:
                detected_language = lang_code
                confidence = lang_confidence
                matched_phrases = lang_matches
    
    return detected_language, confidence, matched_phrases

def test_conversation_scenarios():
    """Test 15 different 10-turn English conversations for false positives"""
    
    conversations = [
        # Conversation 1: General climate questions
        [
            "What is climate change?",
            "How does it affect Toronto?", 
            "What can I do about it?",
            "Are there local programs?",
            "How serious is flooding risk?",
            "What about heat waves?",
            "Can solar panels help?",
            "What about electric vehicles?",
            "How can businesses contribute?",
            "What's the timeline for action?"
        ],
        
        # Conversation 2: Technical climate discussion
        [
            "Explain greenhouse gas emissions",
            "What are carbon offsets?",
            "How do we measure global warming?",
            "What's the role of methane?",
            "Describe carbon capture technology", 
            "How effective are wind farms?",
            "What about nuclear energy?",
            "Explain the carbon cycle",
            "What are tipping points?",
            "How do we track progress?"
        ],
        
        # Conversation 3: Local action and policy
        [
            "What is Toronto doing for climate?",
            "Are there rebates available?", 
            "How can I weatherize my home?",
            "What about public transit?",
            "Are there community gardens?",
            "How do I reduce energy bills?",
            "What grants exist for renewables?",
            "How can schools get involved?", 
            "What about waste reduction?",
            "Where can I volunteer?"
        ],
        
        # Conversation 4: Climate impacts and adaptation
        [
            "How will winters change in Canada?",
            "What about summer temperatures?",
            "Will precipitation patterns shift?",
            "How do we adapt infrastructure?",
            "What crops will grow differently?",
            "How does this affect health?",
            "What about extreme weather?",
            "How do we protect coastlines?",
            "What about water security?",
            "How do ecosystems adapt?"
        ],
        
        # Conversation 5: Energy transition discussion
        [
            "How do we transition from fossil fuels?",
            "What's the role of hydrogen?",
            "Can batteries store enough energy?",
            "How fast can we deploy renewables?",
            "What about grid stability?",
            "How do we heat buildings cleanly?",
            "What role does efficiency play?",
            "How do we electrify transport?",
            "What about industrial processes?",
            "When will we reach net zero?"
        ],
        
        # Conversation 6: Personal action and lifestyle
        [
            "How can I live more sustainably?",
            "What foods have lower emissions?",
            "Should I fly less frequently?",
            "How do I choose green products?",
            "What about my investment portfolio?",
            "How can I influence others?",
            "What's the impact of meat consumption?",
            "Should I buy carbon credits?",
            "How do I make my commute greener?",
            "What's most effective personally?"
        ],
        
        # Conversation 7: Economic aspects
        [
            "What are the costs of climate action?",
            "How do carbon taxes work?",
            "What about green jobs creation?",
            "How do we finance the transition?",
            "What role do banks play?",
            "How do we ensure just transition?",
            "What about stranded assets?",
            "How do we price carbon effectively?",
            "What economic incentives work best?",
            "How do we avoid regressive impacts?"
        ],
        
        # Conversation 8: International cooperation
        [
            "How do countries cooperate on climate?",
            "What was agreed at Paris?",
            "How do we help developing nations?",
            "What about climate financing?",
            "How do we enforce commitments?",
            "What role do cities play globally?",
            "How do we transfer technology?",
            "What about trade and carbon?",
            "How do we address climate migration?",
            "What's next for global action?"
        ],
        
        # Conversation 9: Innovation and technology
        [
            "What breakthrough technologies do we need?",
            "How promising is fusion energy?",
            "Can we engineer the climate?",
            "What about direct air capture?",
            "How do we improve battery storage?",
            "What role will AI play?",
            "How can we make cement cleaner?",
            "What about sustainable aviation?",
            "How do we decarbonize shipping?",
            "What innovations are most promising?"
        ],
        
        # Conversation 10: Agriculture and food
        [
            "How does climate affect agriculture?",
            "What about regenerative farming?",
            "How can we reduce food waste?",
            "What crops are climate resilient?",
            "How do we feed a growing population?",
            "What about vertical farming?",
            "How do we reduce agricultural emissions?",
            "What's the role of soil health?",
            "How do we adapt farming practices?",
            "What about alternative proteins?"
        ],
        
        # Conversation 11: Words that might trigger false positives
        [
            "Point to the main issue",  # Contains 'oi' 
            "Important factors to consider",  # Contains 'por'
            "Doing more for the environment",  # Contains 'oi'
            "Looking at options available",  # Contains 'oi'
            "Supporting local initiatives",  # Contains 'por'
            "Voice your concerns loudly",  # Contains 'oi'
            "Join efforts in your community",  # Contains 'oi'
            "Report problems you encounter",  # Contains 'por'
            "Choice of energy sources",  # Contains 'oi'
            "Corporate responsibility matters"  # Contains 'por'
        ],
        
        # Conversation 12: Common English words with potential matches
        [
            "Going forward with the plan",  # Contains 'oi'
            "Oil companies need regulation",  # Contains 'oi'
            "Boiling point of global action",  # Contains 'oi'
            "Soil quality affects crops",  # Contains 'oi'
            "Toil required for change",  # Contains 'oi'
            "Portfolio diversification needed",  # Contains 'por'
            "Export opportunities in clean tech",  # Contains 'por'
            "Transport sector transformation",  # Contains 'por'
            "Support growing momentum",  # Contains 'por'
            "Report shows clear trends"  # Contains 'por'
        ],
        
        # Conversation 13: Business and policy terms
        [
            "Appointment of climate minister",  # Contains 'oi'
            "Disappointment with slow progress",  # Contains 'oi'
            "Proportion of renewable energy",  # Contains 'por'
            "Corporation climate commitments",  # Contains 'por'
            "Incorporating best practices",  # Contains 'por'
            "Joint venture opportunities",  # Contains 'oi'
            "Point of no return approaching",  # Contains 'oi'
            "Reporting standards implementation",  # Contains 'por'
            "Coordinated global response",  # Contains 'oi'
            "Supporting evidence is clear"  # Contains 'por'
        ],
        
        # Conversation 14: Mixed topics with potential triggers
        [
            "Avoid the worst impacts",  # Contains 'oi'
            "Exploit renewable resources",  # Contains 'oi'
            "Import clean technology",  # Contains 'por'
            "Export climate solutions",  # Contains 'por'
            "Enjoy cleaner air quality",  # Contains 'oi'
            "Deploy new technologies",  # No triggers
            "Employ green workers",  # No triggers
            "Destroy fossil fuel infrastructure",  # Contains 'oi'
            "Spoil corporate profits",  # Contains 'oi'
            "Comfort comes from action"  # No triggers
        ],
        
        # Conversation 15: Complex sentences with multiple potential triggers
        [
            "Joining forces to support important initiatives",  # Contains 'oi' and 'por'
            "Pointing toward corporate responsibility",  # Contains 'oi' and 'por'
            "Reporting disappointing export numbers",  # Contains 'por' and 'oi'
            "Avoiding oil imports from polluting sources",  # Contains 'oi' and 'por'
            "Boiling point in transport sector reform",  # Contains 'oi' and 'por'
            "Supporting important environmental choices",  # Contains 'por' and 'oi'
            "Exploiting opportunities in soil restoration",  # Contains 'oi' and 'por'
            "Incorporating oil-free transport options",  # Contains 'por' and 'oi'
            "Disappointing corporate support levels",  # Contains 'oi' and 'por'
            "Reporting proportional climate responses"  # Contains 'por' and 'oi'
        ]
    ]
    
    print("=== Testing 15 Conversations (10 turns each) for Language Detection False Positives ===\n")
    
    total_queries = 0
    total_false_positives = 0
    false_positive_details = []
    
    for conv_idx, conversation in enumerate(conversations, 1):
        print(f"--- Conversation {conv_idx} ---")
        conv_false_positives = 0
        
        for turn_idx, query in enumerate(conversation, 1):
            total_queries += 1
            detected_lang, confidence, matched_phrases = test_phrase_detection_logic(query)
            
            if detected_lang and detected_lang != 'en':
                total_false_positives += 1
                conv_false_positives += 1
                
                # Check if this would trigger auto-switching (confidence > 0.7)
                would_auto_switch = confidence > 0.7
                
                print(f"  ❌ Turn {turn_idx}: '{query}'")
                print(f"     → Detected: {detected_lang} (confidence: {confidence})")
                print(f"     → Matched phrases: {matched_phrases}")
                print(f"     → Would auto-switch: {'YES' if would_auto_switch else 'NO'}")
                
                false_positive_details.append({
                    'conversation': conv_idx,
                    'turn': turn_idx,
                    'query': query,
                    'detected_lang': detected_lang,
                    'confidence': confidence,
                    'matched_phrases': matched_phrases,
                    'would_auto_switch': would_auto_switch
                })
            else:
                print(f"  ✅ Turn {turn_idx}: No false detection")
        
        if conv_false_positives == 0:
            print(f"  🎉 Conversation {conv_idx}: All clear!")
        else:
            print(f"  ⚠️  Conversation {conv_idx}: {conv_false_positives} false positives")
        print()
    
    # Summary
    print("=== SUMMARY ===")
    print(f"Total queries tested: {total_queries}")
    print(f"Total false positives: {total_false_positives}")
    print(f"False positive rate: {(total_false_positives/total_queries)*100:.1f}%")
    
    # Count auto-switching false positives
    auto_switch_fps = sum(1 for fp in false_positive_details if fp['would_auto_switch'])
    print(f"Would trigger auto-switch: {auto_switch_fps}")
    print(f"Auto-switch false positive rate: {(auto_switch_fps/total_queries)*100:.1f}%")
    
    # Most problematic phrases
    print(f"\n=== MOST PROBLEMATIC PATTERNS ===")
    phrase_counts = {}
    for fp in false_positive_details:
        for phrase in fp['matched_phrases']:
            phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1
    
    if phrase_counts:
        sorted_phrases = sorted(phrase_counts.items(), key=lambda x: x[1], reverse=True)
        for phrase, count in sorted_phrases[:10]:
            print(f"'{phrase}': {count} false matches")
    
    # Languages most commonly falsely detected
    print(f"\n=== LANGUAGES MOST COMMONLY FALSELY DETECTED ===")
    lang_counts = {}
    for fp in false_positive_details:
        lang = fp['detected_lang']
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
    
    if lang_counts:
        sorted_langs = sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)
        for lang, count in sorted_langs:
            print(f"{lang}: {count} false detections")
    
    return total_false_positives, auto_switch_fps, false_positive_details

if __name__ == "__main__":
    test_conversation_scenarios()