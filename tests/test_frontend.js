const query = 'hola como vas?';
const phrases = ['hola', 'gracias', 'hasta luego', 'hasta la vista', 'buenas noches', 'buenos días', 'buenas tardes', 'por favor', 'de nada', 'lo siento', 'perdón', 'disculpe', 'ya me voy', 'nos vemos', 'adiós', 'chao', 'cómo estás', 'como estas', 'qué tal', 'que tal', 'muy bien', 'está bien', 'esta bien'];

const queryLower = query.toLowerCase();
const matchedPhrases = phrases.filter(phrase => {
  const regex = new RegExp(`\\b${phrase.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i');
  const matches = regex.test(queryLower);
  if (matches) console.log(`Matched: ${phrase}`);
  return matches;
});

console.log('All matches:', matchedPhrases);
console.log('Number of matches:', matchedPhrases.length);

const hasMultipleMatches = matchedPhrases.length > 1;
const hasLongPhrase = matchedPhrases.some(phrase => phrase.length > 4);
const hasVeryShortPhrase = matchedPhrases.some(phrase => phrase.length <= 3);

console.log('hasMultipleMatches:', hasMultipleMatches);
console.log('hasLongPhrase:', hasLongPhrase);
console.log('hasVeryShortPhrase:', hasVeryShortPhrase);

let confidence;
if (hasVeryShortPhrase && !hasMultipleMatches && !hasLongPhrase) {
  confidence = 0.3;
} else {
  confidence = (hasMultipleMatches || hasLongPhrase) ? 0.9 : 0.6;
}

console.log('Final confidence:', confidence);
