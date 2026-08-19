/**
 * Lightweight client-side language detection for short greetings and common
 * phrases, used before falling back to the backend detector. Kept out of the
 * page component so the tables are built once, not on every send.
 */

const COMMON_PHRASES_BY_LANGUAGE: Record<string, string[]> = {
  es: ['hola', 'holis', 'holaa', 'ola', 'oli', 'buenas', 'buenos días', 'buenas tardes', 'buenas noches', 'gracias', 'como estas', 'como', 'hasta luego', 'hasta la vista', 'por favor', 'de nada', 'lo siento', 'perdón', 'disculpe', 'ya me voy', 'nos vemos', 'adiós', 'chao', 'cómo estás', 'qué tal', 'que tal', 'muy bien', 'está bien', 'esta bien'],
  fr: ['bonjour', 'bjr', 'salut', 'slt', 'coucou', 'cc', 'merci', 'au revoir', 'à bientôt', 'bonne nuit', 'bonne soirée', "s'il vous plaît", 'de rien', 'désolé', 'pardon', 'excusez-moi', 'comment allez-vous', 'comment ça va', 'ça va', 'très bien', 'ça marche'],
  de: ['hallo', 'halo', 'moin', 'servus', 'guten tag', 'guten morgen', 'morgen', 'danke', 'auf wiedersehen', 'tschüss', 'gute nacht', 'bitte', 'entschuldigung', 'wie geht es dir', 'wie gehts', 'sehr gut'],
  it: ['ciao', 'ciaoo', 'ciaooo', 'buongiorno', 'salve', 'ehi', 'grazie', 'arrivederci', 'buonanotte', 'prego', 'scusa', 'come stai', 'come va', 'molto bene'],
  pt: ['olá', 'ola', 'oi', 'oiii', 'e aí', 'e ai', 'eae', 'salve', 'obrigado', 'obrigada', 'tchau', 'até logo', 'boa noite', 'por favor', 'desculpa', 'como está', 'como vai', 'muito bem'],
  zh: ['你好', '您好', '嗨', '哈喽', '早上好', '谢谢', '再见', '晚安', '请', '对不起', '你怎么样', '很好'],
  ja: ['こんにちは', 'おはよう', 'こんばんは', 'はじめまして', 'もしもし', 'ありがとう', 'さようなら', 'すみません', 'お元気ですか', 'はい'],
  ko: ['안녕하세요', '안녕', '여보세요', '처음 뵙겠습니다', '감사합니다', '안녕히 가세요', '죄송합니다', '어떻게 지내세요', '좋습니다'],
  ru: ['привет', 'приветик', 'здравствуйте', 'здарова', 'добро пожаловать', 'спасибо', 'до свидания', 'пожалуйста', 'извините', 'как дела', 'хорошо'],
  ar: ['مرحبا', 'مرحباً', 'أهلاً', 'أهلا', 'السلام عليكم', 'أهلاً وسهلاً', 'شكرا', 'مع السلامة', 'من فضلك', 'آسف', 'كيف حالك', 'بخير'],
  hi: ['नमस्ते', 'नमस्कार', 'हैलो', 'आदाब', 'धन्यवाद', 'अलविदा', 'कृपया', 'माफ करें', 'आप कैसे हैं', 'अच्छा'],
  nl: ['hallo', 'hoi', 'dag', 'goedemorgen', 'goedemiddag', 'goedenavond', 'dank je', 'tot ziens', 'alsjeblieft', 'sorry', 'hoe gaat het'],
  sv: ['hej', 'hejsan', 'tjena', 'god morgon', 'god kväll', 'tack', 'hej då', 'tack så mycket', 'ursäkta', 'hur mår du', 'bra'],
  da: ['hej', 'hejsa', 'goddag', 'god morgen', 'god aften', 'tak', 'farvel', 'undskyld', 'hvordan har du det', 'godt'],
  no: ['hei', 'heia', 'god morgen', 'god kveld', 'takk', 'ha det', 'unnskyld', 'hvordan har du det', 'bra'],
  fi: ['hei', 'moi', 'terve', 'hyvää huomenta', 'hyvää iltaa', 'kiitos', 'näkemiin', 'anteeksi', 'mitä kuuluu', 'hyvää'],
  pl: ['cześć', 'witaj', 'dzień dobry', 'dobry wieczór', 'dziękuję', 'do widzenia', 'przepraszam', 'jak się masz', 'dobrze'],
  tr: ['merhaba', 'selam', 'selamlar', 'günaydın', 'iyi akşamlar', 'teşekkürler', 'güle güle', 'özür dilerim', 'nasılsın', 'iyi'],
  he: ['שלום', 'היי', 'בוקר טוב', 'ערב טוב', 'תודה', 'להתראות', 'סליחה', 'איך אתה', 'טוב'],
  th: ['สวัสดี', 'หวัดดี', 'สวัสดีครับ', 'สวัสดีค่ะ', 'ขอบคุณ', 'ลาก่อน', 'ขอโทษ', 'สบายดีไหม', 'ดี'],
  vi: ['xin chào', 'chào', 'chào bạn', 'chào anh', 'chào chị', 'cảm ơn', 'tạm biệt', 'xin lỗi', 'bạn khỏe không', 'tốt'],
  uk: ['привіт', 'вітаю', 'здравствуйте', 'добрий день', 'добрий ранок', 'дякую', 'до побачення', 'вибачте', 'як справи', 'добре'],
  bg: ['здравей', 'здрасти', 'добър ден', 'добро утро', 'добър вечер', 'благодаря', 'довиждане', 'извинете', 'как сте', 'добре'],
  cs: ['ahoj', 'čau', 'dobrý den', 'dobré ráno', 'dobrý večer', 'děkuji', 'na shledanou', 'promiňte', 'jak se máte', 'dobře'],
  sk: ['ahoj', 'čau', 'dobrý deň', 'dobré ráno', 'dobrý večer', 'ďakujem', 'dovidenia', 'prepáčte', 'ako sa máte', 'dobre'],
  hr: ['bok', 'zdravo', 'pozdrav', 'dobro jutro', 'dobra večer', 'hvala', 'doviđenja', 'oprostite', 'kako ste', 'dobro'],
  sr: ['здраво', 'ћао', 'поздрав', 'добро јутро', 'добро вече', 'хвала', 'довиђења', 'извините', 'како сте', 'добро'],
  sl: ['zdravo', 'živjo', 'pozdravljeni', 'dobro jutro', 'dober večer', 'hvala', 'nasvidenje', 'oprostite', 'kako ste', 'dobro'],
  ro: ['salut', 'bună', 'bună ziua', 'bună dimineața', 'bună seara', 'mulțumesc', 'la revedere', 'scuzați-mă', 'ce mai faceți', 'bine'],
  hu: ['szia', 'szevasz', 'helló', 'jó napot', 'jó reggelt', 'jó estét', 'köszönöm', 'viszlát', 'elnézést', 'hogy vagy', 'jól'],
};

export type PhraseDetectionResult = {
  language: string;
  confidence: number;
};

/**
 * Detect the language of a short query from common phrases. Returns null when
 * nothing matches; confidence mirrors the previous inline heuristic: multiple
 * or long phrase matches score high, a single very short match scores low.
 */
export function detectLanguageByPhrases(query: string): PhraseDetectionResult | null {
  const queryLower = query.toLowerCase();
  const isMultiWord = queryLower.trim().includes(' ');

  for (const [langCode, phrases] of Object.entries(COMMON_PHRASES_BY_LANGUAGE)) {
    const matchedPhrases = phrases.filter((phrase) => {
      const escapedPhrase = phrase.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      if (isMultiWord) {
        return new RegExp(`\\b${escapedPhrase}\\b`, 'i').test(queryLower);
      }
      return queryLower.trim() === phrase.toLowerCase();
    });

    if (matchedPhrases.length > 0) {
      const hasMultipleMatches = matchedPhrases.length > 1;
      const hasLongPhrase = matchedPhrases.some((phrase) => phrase.length > 4);
      const hasVeryShortPhrase = matchedPhrases.some((phrase) => phrase.length <= 3);

      let confidence: number;
      if (hasVeryShortPhrase && !hasMultipleMatches && !hasLongPhrase) {
        confidence = 0.3;
      } else {
        confidence = hasMultipleMatches || hasLongPhrase ? 0.9 : 0.75;
      }
      return { language: langCode, confidence };
    }
  }

  return null;
}
