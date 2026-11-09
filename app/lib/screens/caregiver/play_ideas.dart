/// Everyday play ideas by age, in the spirit of WHO/UNICEF Care for Child Development:
/// simple activities with things already at home. One idea is shown per day.
class PlayIdea {
  const PlayIdea(this.title, this.body);
  final String title;
  final String body; // {name} is replaced with the child's name
}

const _ideas = <(int, int, List<PlayIdea>)>[
  (0, 5, [
    PlayIdea('Face to face', 'Hold {name} close, smile and talk softly. Pause so {name} can answer with sounds.'),
    PlayIdea('Follow the cloth', 'Move a bright cloth slowly from side to side for {name} to follow with the eyes.'),
    PlayIdea('Tummy time', 'Lay {name} on the tummy for a few minutes while awake, and get down at eye level.'),
  ]),
  (6, 11, [
    PlayIdea('Bang and shake', 'Give {name} a clean cup and spoon to bang, or a closed bottle with seeds to shake.'),
    PlayIdea('Peek-a-boo', 'Hide your face behind a cloth and say "Where is mama?" Then appear with a smile.'),
    PlayIdea('Name it', 'Point to things around the house and name them: cup, ball, door.'),
  ]),
  (12, 23, [
    PlayIdea('Stack and knock', 'Stack two or three tins or cups and let {name} knock them down.'),
    PlayIdea('In and out', 'Let {name} put small safe objects into a container and take them out again.'),
    PlayIdea('Ask simple questions', 'Ask "Where is the cup?" and praise {name} for pointing or bringing it.'),
  ]),
  (24, 35, [
    PlayIdea('Tell a story', 'Tell a short story about your day and ask {name} what happened next.'),
    PlayIdea('Jump together', 'Hold hands and jump with both feet. Count each jump out loud.'),
    PlayIdea('Sort it', 'Sort beans, bottle tops or stones by colour or size together.'),
  ]),
  (36, 59, [
    PlayIdea('Count with me', 'Count spoons, shoes or steps together, up to five, then ten.'),
    PlayIdea('Draw and talk', 'Draw with a stick in the soil or chalk, and ask {name} to tell you about the picture.'),
    PlayIdea('Help me', 'Ask {name} to help with a small task, like setting out cups, and say thank you.'),
  ]),
];

PlayIdea playIdeaFor(int ageMonths, {DateTime? day}) {
  final band = _ideas.firstWhere((b) => ageMonths >= b.$1 && ageMonths <= b.$2,
      orElse: () => _ideas.last);
  final d = day ?? DateTime.now();
  final dayOfYear = d.difference(DateTime(d.year)).inDays;
  return band.$3[dayOfYear % band.$3.length];
}
