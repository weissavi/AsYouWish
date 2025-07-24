window.characterForm = function () {
  return {
    schema: window.__CHARACTER_SCHEMA__ || [],
    formData: {},
    missingFields: [],
    errorMessage: "",
    savingInProgress: false,
	
	

    async init() {
      console.log("🔥 Alpine init()");
      this.schema.forEach(field => {
        this.formData[field.field] = field.render === "checkbox" ? [] : "";
      });
    },

    updateCheckbox(field, value, checked) {
      const values = this.formData[field] || [];
      if (checked) values.push(value);
      else this.formData[field] = values.filter(v => v !== value);
    },

    async submitForm() {
	  console.log("submitForm");

      if (this.savingInProgress) return;
      this.savingInProgress = true;

/*       this.missingFields = this.schema
        .filter(f => f.mandatory === "yes")
        .filter(f => !this.formData[f.field] || (Array.isArray(this.formData[f.field]) && this.formData[f.field].length === 0))
        .map(f => f.field); */
		
		
		//console.log("formData snapshot:", JSON.stringify(this.formData, null, 2));
		
		/* console.log("----- DEBUG FORM DATA -----");
		this.schema.forEach(f => {
		  const val = this.formData[f.field];
		  console.log(`${f.field}:`, val, "| typeof:", typeof val, "| isArray:", Array.isArray(val));
		}); */

		this.missingFields = this.schema
		  .filter(f => this.isMandatoryAndVisible(f))
		  .filter(f => this.isEmpty(this.formData[f.field]))
		  .map(f => f.field);



		//console.log("missingFields : " + this.missingFields.length);
		//this.missingFields.forEach(field => console.log("❌ Missing:", field));

		
      if (this.missingFields.length > 0) {
        this.savingInProgress = false;
        return;
      }

      const response = await fetch("/save_character", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(this.formData)
      });

      this.savingInProgress = false;

	  if (response.ok) {
		  showToast("Character saved");
		  showCharacterList();
	  } else {
		  if (response.status === 403) {
			showToast("Your session has expired. Redirecting to login...");
			window.location.href = "/login";  // או "/" אם אתה רוצה לדף הבית
			return;
		  }
		  else {
			  showToast("save error " + response.error);
		  }
	  }
    },
	
	isEmpty(val) {
	  const realType = Object.prototype.toString.call(val);

	  if (realType === "[object Array]") return val.length === 0;
	  if (typeof val === "object" && val !== null) return Object.keys(val).length === 0;
	  if (val === null || val === undefined) return true;

	  const str = String(val).trim().toLowerCase();
	  return str === "" || str === "none" || str === "default" || str === "soft";
	},
	
	fieldVisible(field) {
	  if (!field.condition || field.condition === 'always') return true;
	  try {
		// 👇 ניתוח נכון שמודע לתלות ב־formData
		const condition = field.condition;
		const keys = Object.keys(this.formData);
		const context = new Function(...keys, `return (${condition});`);
		return context(...keys.map(k => this.formData[k]));
	  } catch (e) {
		console.error("fieldVisible error:", e, field.condition);
		return false;
	  }
	},
	
	isMandatoryAndVisible(field) {
	  if (field.mandatory !== "yes") return false;
	  return this.fieldVisible(field);
	},


    resetForm() {
      this.formData = {};
      for (const field of this.schema) {
        this.formData[field.field] = field.render === "checkbox" ? [] : "";
      }
      this.errorMessage = "";
      this.missingFields = [];
    },

    closePanel() {
      this.resetForm();
      showPanels('story-section')
    },
	
	getRandomText(label) {
	  const samples = [
		"Just exploring...",
		"Curious and open-minded",
		"Looking for connection",
		"Ready to try new things",
		"Deep fantasies await",
		"Let's discover together",
		"Mix of wild and tender",
		"Surprise me",
		"This is my secret spot"
	  ];

	  const rand = samples[Math.floor(Math.random() * samples.length)];
	  return `${label}: ${rand}`;
	},
	
	fillTestData() {
	  const getRandomFromArray = arr => arr[Math.floor(Math.random() * arr.length)];
	  const getRandomInt = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;
	  
	  const maleNames = ["Jake", "Liam", "Ethan", "Leo", "Max", "Connor", "Axel", "Dominic"];
	  const femaleNames = ["Luna", "Sophie", "Ava", "Maya", "Ella", "Chloe", "Riley", "Zoe"];
	  const neutralNames = ["Sky", "River", "Phoenix", "Sage", "Ash", "Indigo", "Quinn", "Emery"];
	  const otherGenders = [
		"Alien-wolf hybrid", "Shape-shifter", "Cyborg queen", "Mythical beast",
		"Artificial spirit", "Living scent cloud", "Quantum lover", "Energy entity"
	  ];	  

	  const textPresets = {
		goal: [
		  "To explore dominance safely.",
		  "To learn how to submit.",
		  "To unlock hidden desires.",
		  "To try new roleplay scenarios.",
		  "To experience sensual control.",
		  "To test my limits playfully.",
		  "To connect emotionally through power.",
		  "To feel wanted and used.",
		  "To develop self-understanding.",
		  "To be surprised and trained."
		],
		traits: [
		  "Submissive, curious, soft-spoken.",
		  "Confident, controlling, loyal.",
		  "Playful, obedient, passionate.",
		  "Analytical, sensual, deep thinker.",
		  "Experimental, brave, respectful.",
		  "Quiet, eager to please, gentle.",
		  "Spontaneous, tender, obedient.",
		  "Assertive, teasing, patient.",
		  "Rebellious, flirty, open-minded.",
		  "Sensitive, alert, giving."
		],
		limits: [
		  "No pain, no blood, no force.",
		  "No humiliation, no breath play.",
		  "No public play or degradation.",
		  "No restraint, no anal, no degradation.",
		  "No unsafe tools or non-consensual play.",
		  "No impact marks or role reversal.",
		  "Only soft limits respected.",
		  "No toys, only body.",
		  "No control loss or gagging.",
		  "All activity must be explained before play."
		],
		kinks_fetishes: [
		  "Praise kink, sensory play, teasing.",
		  "Bondage, blindfolds, light spanking.",
		  "Role reversal, oral worship, dirty talk.",
		  "Pet play, obedience, rituals.",
		  "Nipple play, power imbalance, inspection.",
		  "Verbal submission, edge play, gentle force.",
		  "Service kink, licking, restrained begging.",
		  "Clothing control, eye contact, collaring.",
		  "Voice play, guided touch, breath rhythm.",
		  "Fantasy roleplay, age dynamics, scent focus."
		],
		fantasies: [
		  "Being led and trained slowly.",
		  "Worshipping a voice without seeing them.",
		  "Being displayed while others watch.",
		  "Tied, blindfolded, and guided.",
		  "Used repeatedly by a trusted partner.",
		  "Begging for release under control.",
		  "Teased with scent and whispers.",
		  "Overstimulated with praise and denial.",
		  "Serving multiple strangers under command.",
		  "Made to reveal desires aloud while being touched."
		]
	  };

	  this.schema.forEach(field => {
		const name = field.field;

		// 1. שדות עם options מתוך הסכמה
		if (field.options && Array.isArray(field.options)) {
		  const values = field.options.map(opt => opt.value || opt);

		  if (field.render === "checkbox") {
			const shuffled = [...values].sort(() => 0.5 - Math.random());
			this.formData[name] = shuffled.slice(0, getRandomInt(1, Math.min(3, values.length)));
		  } else {
			this.formData[name] = getRandomFromArray(values);
		  }
		}

		// 2. שדות טקסט חופשי — מתוך מאגר עשיר
		else if (textPresets[name]) {
		  this.formData[name] = getRandomFromArray(textPresets[name]);
		}

		// 3. מספריים
		else if (name === "age") {
		  this.formData[name] = getRandomInt(18, 40);
		} else if (name === "weight_kg") {
		  this.formData[name] = getRandomInt(50, 95);
		} else if (name === "height_cm") {
		  this.formData[name] = getRandomInt(155, 200);
		}

		// 4. מין מיוחד = other_gender
		else if (name === "gender" && this.formData["gender"] === "Something else") {
		  this.formData["other_gender"] = getRandomFromArray(otherGenders);
		}

		// 5. fallback לשדות שלא תפסו — רק טקסט כללי
		else if (name === "other_gender") {
		  this.formData["name"] = getRandomFromArray([...maleNames, ...femaleNames, ...neutralNames]);
		  this.formData["other_gender"] = getRandomFromArray(otherGenders);
		}
		
		
/* 		if (name === "content_types") {
		  const values = field.options.map(opt => opt.key || opt.value || opt.label);
		  const shuffled = [...values].sort(() => 0.5 - Math.random());
		  this.formData[name] = shuffled.slice(0, getRandomInt(2, 5)); // בין 2 ל־5 ערכים
		  return;
		} */
		if (name === "content_types") {
		  const values = field.options.map(opt => opt.value || opt.key || opt.label);
		  const shuffled = [...values].sort(() => 0.5 - Math.random());
		  // העתק חדש של המערך כדי להבטיח ריאקטיביות
		  this.formData[name] = [...shuffled.slice(0, getRandomInt(2, Math.min(5, values.length)))];
		  
		// עדכון ידני של הצ'קבוקסים בטופס
		const selectedTypes = this.formData["content_types"];
		document.querySelectorAll('input[type="checkbox"][name="content_types"]').forEach(cb => {
		  cb.checked = selectedTypes.includes(cb.value);
		});
		  
		}
		
	  });

	  // נבחר את המגדר קודם
	  const genderField = this.schema.find(f => f.field === "gender");
	  const genderOptions = genderField.options.map(opt => opt.value);
	  const selectedGender = getRandomFromArray(genderOptions);
	  this.formData["gender"] = selectedGender;

	  // שם בהתאם למגדר
	  if (selectedGender === "Male") {
		this.formData["name"] = getRandomFromArray(maleNames);
	  } else if (selectedGender === "Female") {
		this.formData["name"] = getRandomFromArray(femaleNames);
	  } else if (selectedGender === "Non Binary") {
		this.formData["name"] = getRandomFromArray(neutralNames);
	  } else if (selectedGender === "Something else") {
		this.formData["name"] = getRandomFromArray([...maleNames, ...femaleNames, ...neutralNames]);
		this.formData["other_gender"] = getRandomFromArray(otherGenders);
	  }
	  
	  if (this.formData["gender"] != "Something else") {
			this.formData["other_gender"] = ''
	  }
	  
		str=''
		this.schema.forEach(f => {
		  const val = this.formData[f.field];
		  str += f.field + " : " + val + "\n"
		  
		});	  
		console.log(str);

	}


  };
};


	
