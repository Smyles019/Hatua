/// The assistant's danger-sign screen (backend app/services/assistant.py, DANGER), kept
/// on the phone too, so a question about a danger sign gets the "go to a health facility
/// now" answer even with no connection. Keep the two lists the same.
final _danger = [
  r'convuls', r'seizure', r'\b(having|has|had|a|having a) fits?\b', r'\bfitting\b',
  r'degedege', r'kifafa',
  r"(not|n't|cannot|can't|unable to|struggl\w* to|hard to|trouble) breath",
  r'(fast|difficult|rapid|noisy) breathing', r'breathing (fast|very fast|with difficulty)',
  r'hapumui', r'anapumua (kwa shida|haraka)', r'kupumua kwa shida',
  r'blood in (the |his |her )?(stool|poo|poop|nappy|diaper)', r'bloody (stool|poo)',
  r'damu (kwenye|katika) (kinyesi|choo)',
  r"(not|n't|cannot|can't|won't|will not|refus\w*( to)?) (drink|breastfeed|feed|suck)",
  r"(not|n't) (drinking|breastfeeding|feeding|sucking)", r'hawezi kunywa', r'hanyonyi',
  r'unconscious', r"(won't|will not|can't|cannot|hard to|not) wak",
  r'hazinduki', r'hajitambui', r'very sleepy',
  r'yellow (eyes|skin|palms|soles)', r'(eyes|skin) (look |are |is )?yellow', r'manjano',
].map(RegExp.new).toList();

// A fever, or feeling very hot or very cold, in a baby under 2 months (backend FEVER and
// YOUNG). Offline the phone only has the words, so the age must be in the question.
final _fever = [
  r'fever', r'\bhot\b', r'temperature', r'(very|too) cold', r'\bhoma\b', r'joto', r'baridi sana',
].map(RegExp.new).toList();
final _young = [
  r'\b([1-8]|one|two|three|four|five|six|seven|eight)[ -]?(weeks?|wks?)\b',
  r'\b\d{1,2}[ -]?days?[ -]old\b', r'new ?born', r'\b1[ -]?month[ -]old\b', r'one month old',
  r'mtoto mchanga', r'wiki (moja|mbili|tatu|nne|tano|sita|saba|nane|[1-8])\b', r'siku \d',
].map(RegExp.new).toList();

bool mentionsDangerSign(String text) {
  final t = text.toLowerCase().split(RegExp(r'\s+')).where((w) => w.isNotEmpty).join(' ');
  if (_danger.any((p) => p.hasMatch(t))) return true;
  return _young.any((p) => p.hasMatch(t)) && _fever.any((p) => p.hasMatch(t));
}

/// The fixed reply, word for word the backend's URGENT (translated with tr()).
const urgentReply = 'This could be a danger sign. Take your child to a health facility now. '
    'Do not wait for an answer here. If you can, call your community health worker on the way.';
