"""
Simple test script - runs final_graph and saves results to test_result.json
"""

from llm import final_graph
import json

conversations = [{'user': 'alex',
                  'message': 'Have you looked into ClawDBot lately? Something feels off about how much data it\'s pulling.',
                  'date': 1769594405,
                  'message_id': 0},
                 {'user': 'sam',
                  'message': 'Yeah, I noticed that too. It\'s not just metadata, it\'s actually reading message contents.',
                  'date': 1769594440,
                  'message_id': 1},
                 {'user': 'alex',
                  'message': 'Exactly. That goes way beyond what they mention in their privacy policy.',
                  'date': 1769594475,
                  'message_id': 2},
                 {'user': 'sam',
                  'message': 'The scary part is it\'s happening silently. No clear opt-in, no warning.',
                  'date': 1769594510,
                  'message_id': 3},
                 {'user': 'alex',
                  'message': 'If this gets out, it\'s a massive trust violation. Almost spyware-level behavior.',
                  'date': 1769594550,
                  'message_id': 4},
                 {'user': 'sam',
                  'message': 'I\'m surprised more people aren\'t talking about it yet. This could blow up.',
                  'date': 1769594600,
                  'message_id': 5},
                 {'user': 'alex',
                  'message': 'Switching gears — have you heard the new STT models that dropped last week?',
                  'date': 1769596205,
                  'message_id': 6},
                 {'user': 'sam',
                  'message': 'Bro yes 😂 they\'re scary good. ElevenLabs must be sweating right now.',
                  'date': 1769596250,
                  'message_id': 7},
                 {'user': 'alex',
                  'message': 'For real. Latency is lower and accents are handled way better.',
                  'date': 1769596290,
                  'message_id': 8},
                 {'user': 'sam',
                  'message': 'I tested one with background noise and it still nailed the transcript.',
                  'date': 1769596330,
                  'message_id': 9},
                 {'user': 'alex',
                  'message': 'If pricing stays sane, this is going to eat a chunk of ElevenLabs\' use cases.',
                  'date': 1769596370,
                  'message_id': 10},
                 {'user': 'sam',
                  'message': 'ElevenLabs be like: adding \'emotional whisper v4\' won\'t save us 💀',
                  'date': 1769596410,
                  'message_id': 11},
                 {'user': 'alex',
                  'message': 'Haha seriously. Accuracy beats fancy voices any day.',
                  'date': 1769596450,
                  'message_id': 12},
                 {'user': 'sam',
                  'message': 'Give it a month and every demo app will be using the new STT.',
                  'date': 1769596490,
                  'message_id': 13},
                 {'user': 'alex',
                  'message': 'And every founder will say it\'s \'just an experiment\'. Classic.',
                  'date': 1769596530,
                  'message_id': 14},
                 {'user': 'sam',
                  'message': 'Meanwhile ElevenLabs marketing team pulling all-nighters.',
                  'date': 1769596555,
                  'message_id': 15},
                 {'user': 'alex',
                  'message': 'Random question — what\'s your max deadlift these days?',
                  'date': 1769601605,
                  'message_id': 16},
                 {'user': 'sam',
                  'message': '120 lbs for reps. Not huge, but I can do like 12 clean.',
                  'date': 1769601650,
                  'message_id': 17},
                 {'user': 'alex',
                  'message': '12 reps at 120 is solid. Form still tight on the last few?',
                  'date': 1769601690,
                  'message_id': 18},
                 {'user': 'sam',
                  'message': 'Yeah, last 2 are a grind but no rounding. Lower back feels fine.',
                  'date': 1769601725,
                  'message_id': 19}]

if __name__ == "__main__":
    print("Running final_graph...")
    result = final_graph.invoke({
        'messages': conversations,
        'max_iterations_per_job': 3
    })

    print(f"Graph execution completed!")
    print(f"Total jobs: {len(result['jobs_result'])}")

    # Save to JSON
    with open('test_result.json', 'w') as f:
        json.dump(result, f, indent=2, default=str)

    print("Results saved to test_result.json")
