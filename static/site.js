function openCharacterCreationPanel() {
  document.getElementById('story-section').classList.add('hidden');
  document.getElementById('character-creation-section').classList.remove('hidden');
}

function closeCharacterCreationPanel() {
  document.getElementById('character-creation-section').classList.add('hidden');
  document.getElementById('story-section').classList.remove('hidden');
}
