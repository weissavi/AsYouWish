function showPanels(leftPanel, rightPanel) {
  // החבא את כל הפאנלים עם data-panel
  document.querySelectorAll("[data-panel]").forEach(el => {
    el.classList.add("hidden");
  });
  if (!rightPanel)
	 rightPanel="scene-section"	
	
  panelIds = [leftPanel,rightPanel]	
  // הצג את הפאנלים המבוקשים
  panelIds.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.remove("hidden");
  });

}


function showToast(message, duration = 3000) {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.classList.remove('hidden');
  toast.classList.add('opacity-100');

  setTimeout(() => {
    toast.classList.add('hidden');
    toast.classList.remove('opacity-100');
  }, duration);
}


function showCharacterList() {
  showPanels('character-list-section');
  if (characterPanel) {
    characterPanel.loadCharacters(); // ריענון ידני בכל פתיחה
  }
}
let characterPanel = null;

function characterListForm() {
  return {
    characters: [],
    prompt: "",
    selected: "",

    async loadCharacters() {
      const res = await fetch('/list_characters');
      const data = await res.json();
      this.characters = data.characters || [];
    },

    init() {
      characterPanel = this; // שמור רפרנס לפאנל הראשי
      this.loadCharacters();
    },

	async deleteCharacter(name) {
	  if (!confirm(`Delete ${name}?`)) return;
	  try {
		const res = await fetch(`/delete_character/${name}`, { method: 'DELETE' });
		const data = await res.json();
		if (data.success) {
		  this.loadCharacters();
		  showToast(`Deleted ${name}`);
		} else {
		  showToast("Failed to delete.");
		}
	  } catch (e) {
		console.error(e);
		showToast("Error during deletion.");
	  }
	},


    async loadPrompt(name) {
      this.prompt = "Loading...";
      this.selected = name;
      try {
        const res = await fetch(`/prompt/${name}`);
        this.prompt = await res.text();
      } catch (err) {
        this.prompt = "❌ Failed to load prompt.";
        console.error(err);
      }
    },
    closePanel() {
      showPanels('story-section')
    }
	
  };
}

