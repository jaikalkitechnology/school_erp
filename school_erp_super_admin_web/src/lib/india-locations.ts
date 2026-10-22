/**
 * Indian states / union territories and their cities, for the State and
 * City dropdowns. Cities are every district headquarters plus the other
 * major towns; smaller places can still be typed in by hand.
 */
const CITIES_BY_STATE: Record<string, string[]> = {
  "Andhra Pradesh": [
    "Visakhapatnam", "Vijayawada", "Guntur", "Nellore", "Kurnool", "Kakinada", "Rajamahendravaram",
    "Tirupati", "Kadapa", "Anantapur", "Eluru", "Ongole", "Vizianagaram", "Srikakulam", "Chittoor",
    "Machilipatnam", "Bhimavaram", "Amalapuram", "Anakapalli", "Paderu", "Narasaraopet", "Bapatla",
    "Puttaparthi", "Nandyal", "Rayachoti", "Tenali", "Proddatur", "Hindupur", "Adoni", "Guntakal",
    "Dharmavaram", "Madanapalle", "Kavali", "Chirala", "Gudivada", "Tadepalligudem", "Srikalahasti",
    "Amaravati", "Mangalagiri", "Tadipatri", "Palakollu", "Narsipatnam",
  ],
  "Arunachal Pradesh": [
    "Itanagar", "Naharlagun", "Pasighat", "Tawang", "Bomdila", "Ziro", "Aalo", "Tezu", "Roing", "Khonsa",
    "Changlang", "Daporijo", "Seppa", "Yingkiong", "Namsai", "Anini", "Koloriang", "Basar", "Longding",
    "Hawai", "Tato", "Lemmi", "Palin", "Dirang", "Miao",
  ],
  Assam: [
    "Guwahati", "Dispur", "Silchar", "Dibrugarh", "Jorhat", "Nagaon", "Tinsukia", "Tezpur", "Bongaigaon",
    "Dhubri", "Diphu", "North Lakhimpur", "Karimganj", "Sivasagar", "Goalpara", "Barpeta", "Mangaldai",
    "Nalbari", "Golaghat", "Haflong", "Kokrajhar", "Hailakandi", "Morigaon", "Dhemaji", "Hojai", "Udalguri",
    "Biswanath Chariali", "Majuli", "Hamren", "Hatsingimari", "Kajalgaon", "Mushalpur", "Pathsala", "Bijni",
    "Abhayapuri", "Lumding", "Duliajan", "Digboi", "Margherita", "Mankachar", "Sonari", "Rangia",
  ],
  Bihar: [
    "Patna", "Gaya", "Bhagalpur", "Muzaffarpur", "Darbhanga", "Purnia", "Arrah", "Begusarai", "Katihar",
    "Munger", "Chapra", "Sasaram", "Hajipur", "Dehri", "Siwan", "Motihari", "Bettiah", "Nawada",
    "Bihar Sharif", "Buxar", "Kishanganj", "Sitamarhi", "Jamalpur", "Jehanabad", "Aurangabad", "Madhubani",
    "Samastipur", "Saharsa", "Supaul", "Madhepura", "Araria", "Khagaria", "Lakhisarai", "Sheikhpura",
    "Jamui", "Banka", "Bhabua", "Arwal", "Gopalganj", "Sheohar", "Bodh Gaya", "Rajgir", "Danapur", "Hilsa",
    "Barh", "Mokama", "Dumraon", "Forbesganj", "Raxaul", "Narkatiaganj", "Bagaha",
  ],
  Chhattisgarh: [
    "Raipur", "Bhilai", "Durg", "Bilaspur", "Korba", "Rajnandgaon", "Raigarh", "Jagdalpur", "Ambikapur",
    "Dhamtari", "Mahasamund", "Kanker", "Kondagaon", "Narayanpur", "Bijapur", "Dantewada", "Sukma",
    "Kawardha", "Mungeli", "Janjgir", "Baloda Bazar", "Gariaband", "Balod", "Bemetara", "Surajpur",
    "Balrampur", "Jashpur Nagar", "Baikunthpur", "Gaurela", "Manendragarh", "Khairagarh", "Mohla", "Sakti",
    "Sarangarh", "Chirmiri", "Nava Raipur", "Kumhari", "Tilda",
  ],
  Goa: [
    "Panaji", "Margao", "Vasco da Gama", "Mapusa", "Ponda", "Bicholim", "Curchorem", "Valpoi", "Sanguem",
    "Canacona", "Quepem", "Pernem", "Calangute", "Old Goa",
  ],
  Gujarat: [
    "Ahmedabad", "Surat", "Vadodara", "Rajkot", "Bhavnagar", "Jamnagar", "Gandhinagar", "Junagadh", "Anand",
    "Nadiad", "Morbi", "Gandhidham", "Bhuj", "Porbandar", "Navsari", "Valsad", "Vapi", "Bharuch",
    "Ankleshwar", "Mehsana", "Palanpur", "Patan", "Himmatnagar", "Godhra", "Dahod", "Surendranagar",
    "Amreli", "Botad", "Veraval", "Dwarka", "Khambhalia", "Modasa", "Lunawada", "Chhota Udaipur",
    "Rajpipla", "Vyara", "Ahwa", "Deesa", "Unjha", "Kalol", "Gondal", "Jetpur", "Wadhwan", "Mundra",
    "Anjar", "Mandvi", "Bardoli", "Sanand", "Dholka", "Viramgam", "Mahuva", "Palitana", "Keshod", "Upleta",
    "Dhoraji", "Siddhpur",
  ],
  Haryana: [
    "Gurugram", "Faridabad", "Panipat", "Ambala", "Yamunanagar", "Rohtak", "Hisar", "Karnal", "Sonipat",
    "Panchkula", "Bhiwani", "Sirsa", "Bahadurgarh", "Jind", "Thanesar", "Kurukshetra", "Kaithal", "Rewari",
    "Palwal", "Narnaul", "Fatehabad", "Jhajjar", "Charkhi Dadri", "Nuh", "Hansi", "Mahendragarh", "Tohana",
    "Gohana", "Jagadhri", "Pehowa", "Manesar",
  ],
  "Himachal Pradesh": [
    "Shimla", "Dharamshala", "Solan", "Mandi", "Kullu", "Manali", "Hamirpur", "Una", "Bilaspur", "Chamba",
    "Nahan", "Keylong", "Reckong Peo", "Palampur", "Baddi", "Nalagarh", "Paonta Sahib", "Sundernagar",
    "Kangra", "Dalhousie", "Kasauli", "McLeod Ganj",
  ],
  Jharkhand: [
    "Ranchi", "Jamshedpur", "Dhanbad", "Bokaro Steel City", "Deoghar", "Hazaribagh", "Giridih", "Ramgarh",
    "Medininagar", "Chaibasa", "Dumka", "Phusro", "Jhumri Telaiya", "Koderma", "Sahibganj", "Pakur",
    "Godda", "Jamtara", "Chatra", "Gumla", "Lohardaga", "Simdega", "Khunti", "Latehar", "Garhwa",
    "Seraikela", "Adityapur", "Madhupur", "Chirkunda",
  ],
  Karnataka: [
    "Bengaluru", "Mysuru", "Mangaluru", "Hubballi", "Dharwad", "Belagavi", "Kalaburagi", "Ballari",
    "Vijayapura", "Shivamogga", "Tumakuru", "Davanagere", "Raichur", "Bidar", "Hosapete", "Udupi", "Hassan",
    "Chitradurga", "Mandya", "Kolar", "Chikkamagaluru", "Gadag", "Bagalkot", "Haveri", "Karwar", "Koppal",
    "Chamarajanagar", "Madikeri", "Yadgir", "Chikkaballapur", "Ramanagara", "Doddaballapura",
    "Robertsonpet", "Bhadravati", "Gangavati", "Sirsi", "Puttur", "Bhatkal", "Gokak", "Nippani",
    "Channapatna", "Hoskote", "Kundapura", "Manipal", "Dandeli",
  ],
  Kerala: [
    "Thiruvananthapuram", "Kochi", "Kozhikode", "Thrissur", "Kollam", "Kannur", "Alappuzha", "Palakkad",
    "Kottayam", "Malappuram", "Kasaragod", "Pathanamthitta", "Painavu", "Kalpetta", "Thodupuzha", "Munnar",
    "Guruvayur", "Tirur", "Manjeri", "Ponnani", "Vadakara", "Thalassery", "Kayamkulam", "Changanassery",
    "Aluva", "Perumbavoor", "Muvattupuzha", "Kothamangalam", "Ernakulam", "Kodungallur", "Chalakudy",
    "Ottapalam", "Nilambur", "Payyanur", "Kanhangad", "Neyyattinkara", "Varkala", "Attingal",
    "Karunagappally", "Punalur", "Adoor", "Thiruvalla", "Pala",
  ],
  "Madhya Pradesh": [
    "Bhopal", "Indore", "Jabalpur", "Gwalior", "Ujjain", "Sagar", "Dewas", "Satna", "Ratlam", "Rewa", "Katni",
    "Singrauli", "Burhanpur", "Khandwa", "Bhind", "Chhindwara", "Guna", "Shivpuri", "Vidisha", "Chhatarpur",
    "Damoh", "Mandsaur", "Khargone", "Neemuch", "Pithampur", "Narmadapuram", "Itarsi", "Sehore", "Betul",
    "Seoni", "Datia", "Nagda", "Shahdol", "Dhar", "Balaghat", "Mandla", "Dindori", "Umaria", "Anuppur",
    "Sidhi", "Tikamgarh", "Niwari", "Panna", "Raisen", "Rajgarh", "Shajapur", "Agar Malwa", "Jhabua",
    "Alirajpur", "Barwani", "Sheopur", "Morena", "Ashoknagar", "Harda", "Narsinghpur", "Mauganj", "Maihar",
    "Pandhurna", "Mhow",
  ],
  Maharashtra: [
    "Mumbai", "Pune", "Nagpur", "Thane", "Nashik", "Chhatrapati Sambhajinagar (Aurangabad)", "Solapur",
    "Navi Mumbai", "Kalyan", "Dombivli", "Vasai-Virar", "Bhiwandi", "Mira-Bhayandar", "Ulhasnagar", "Panvel",
    "Pimpri-Chinchwad", "Kolhapur", "Amravati", "Akola", "Latur", "Dhule", "Jalgaon", "Sangli", "Satara",
    "Ratnagiri", "Oros", "Chandrapur", "Parbhani", "Nanded", "Jalna", "Beed", "Hingoli", "Washim",
    "Buldhana", "Yavatmal", "Wardha", "Bhandara", "Gondia", "Gadchiroli", "Nandurbar", "Palghar", "Alibag",
    "Ahilyanagar (Ahmednagar)", "Dharashiv (Osmanabad)", "Ichalkaranji", "Malegaon", "Baramati", "Karad",
    "Lonavala", "Shirdi", "Pandharpur", "Barshi", "Udgir", "Ambajogai", "Achalpur", "Bhusawal", "Badlapur",
    "Ambernath", "Mahad", "Chiplun", "Sawantwadi", "Kamptee",
  ],
  Manipur: [
    "Imphal", "Thoubal", "Bishnupur", "Churachandpur", "Ukhrul", "Senapati", "Tamenglong", "Chandel",
    "Jiribam", "Kakching", "Kangpokpi", "Noney", "Pherzawl", "Tengnoupal", "Kamjong", "Moirang", "Moreh",
  ],
  Meghalaya: [
    "Shillong", "Tura", "Jowai", "Nongstoin", "Nongpoh", "Williamnagar", "Baghmara", "Resubelpara",
    "Ampati", "Mawkyrwat", "Khliehriat", "Mairang", "Sohra",
  ],
  Mizoram: [
    "Aizawl", "Lunglei", "Champhai", "Serchhip", "Kolasib", "Saiha", "Lawngtlai", "Mamit", "Khawzawl",
    "Hnahthial", "Saitual", "Vairengte",
  ],
  Nagaland: [
    "Kohima", "Dimapur", "Mokokchung", "Tuensang", "Wokha", "Zunheboto", "Mon", "Phek", "Kiphire",
    "Longleng", "Peren", "Noklak", "Chumoukedima", "Niuland", "Tseminyu", "Shamator",
  ],
  Odisha: [
    "Bhubaneswar", "Cuttack", "Rourkela", "Berhampur", "Sambalpur", "Puri", "Balasore", "Bhadrak", "Baripada",
    "Balangir", "Jharsuguda", "Jeypore", "Bargarh", "Rayagada", "Koraput", "Angul", "Dhenkanal", "Kendrapara",
    "Jagatsinghpur", "Jajpur", "Keonjhar", "Paradip", "Sundargarh", "Bhawanipatna", "Nabarangpur",
    "Malkangiri", "Phulbani", "Nuapada", "Sonepur", "Boudh", "Deogarh", "Nayagarh", "Khordha", "Gunupur",
    "Paralakhemundi", "Talcher", "Brajrajnagar", "Rajgangpur", "Konark", "Chhatrapur", "Aska",
  ],
  Punjab: [
    "Ludhiana", "Amritsar", "Jalandhar", "Patiala", "Bathinda", "Mohali", "Hoshiarpur", "Pathankot", "Moga",
    "Batala", "Abohar", "Malerkotla", "Khanna", "Phagwara", "Sri Muktsar Sahib", "Barnala", "Rajpura",
    "Firozpur", "Kapurthala", "Faridkot", "Sangrur", "Fazilka", "Gurdaspur", "Mansa", "Rupnagar",
    "Nawanshahr", "Tarn Taran", "Fatehgarh Sahib", "Zirakpur", "Kharar", "Sunam", "Anandpur Sahib",
  ],
  Rajasthan: [
    "Jaipur", "Jodhpur", "Kota", "Bikaner", "Ajmer", "Udaipur", "Bhilwara", "Alwar", "Bharatpur", "Sikar",
    "Pali", "Sri Ganganagar", "Tonk", "Kishangarh", "Beawar", "Hanumangarh", "Dholpur", "Gangapur City",
    "Sawai Madhopur", "Churu", "Jhunjhunu", "Baran", "Bundi", "Chittorgarh", "Banswara", "Dungarpur",
    "Barmer", "Jaisalmer", "Jalore", "Sirohi", "Mount Abu", "Nagaur", "Rajsamand", "Pratapgarh", "Karauli",
    "Dausa", "Jhalawar", "Kotputli", "Balotra", "Didwana", "Kuchaman City", "Deeg", "Khairthal",
    "Salumbar", "Phalodi", "Makrana", "Sujangarh", "Nathdwara", "Pushkar", "Bhiwadi", "Neem Ka Thana",
    "Hindaun",
  ],
  Sikkim: [
    "Gangtok", "Namchi", "Mangan", "Gyalshing", "Pakyong", "Soreng", "Rangpo", "Singtam", "Jorethang",
    "Ravangla", "Pelling", "Lachung",
  ],
  "Tamil Nadu": [
    "Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem", "Tirunelveli", "Tiruppur", "Vellore",
    "Erode", "Thoothukudi", "Dindigul", "Thanjavur", "Ranipet", "Sivakasi", "Karur", "Udhagamandalam (Ooty)",
    "Hosur", "Nagercoil", "Kanchipuram", "Kumbakonam", "Cuddalore", "Tiruvannamalai", "Pollachi",
    "Rajapalayam", "Pudukkottai", "Neyveli", "Nagapattinam", "Viluppuram", "Krishnagiri", "Dharmapuri",
    "Namakkal", "Perambalur", "Ariyalur", "Sivaganga", "Karaikudi", "Virudhunagar", "Ramanathapuram",
    "Theni", "Tiruvallur", "Tiruvarur", "Mayiladuthurai", "Chengalpattu", "Kallakurichi", "Tenkasi",
    "Tirupattur", "Avadi", "Tambaram", "Ambattur", "Gudiyatham", "Arakkonam", "Kodaikanal", "Rameswaram",
    "Mettupalayam", "Gobichettipalayam", "Palani", "Kovilpatti",
  ],
  Telangana: [
    "Hyderabad", "Secunderabad", "Warangal", "Hanamkonda", "Nizamabad", "Karimnagar", "Khammam", "Ramagundam",
    "Mahbubnagar", "Nalgonda", "Adilabad", "Suryapet", "Miryalaguda", "Siddipet", "Jagtial", "Mancherial",
    "Kothagudem", "Sangareddy", "Medak", "Kamareddy", "Nirmal", "Wanaparthy", "Nagarkurnool", "Gadwal",
    "Vikarabad", "Jangaon", "Bhongir", "Sircilla", "Peddapalli", "Bhupalpally", "Mulugu", "Narayanpet",
    "Mahabubabad", "Asifabad", "Medchal", "Shamshabad", "Bodhan", "Kodad", "Tandur", "Bellampalli", "Gajwel",
  ],
  Tripura: [
    "Agartala", "Udaipur", "Dharmanagar", "Kailashahar", "Ambassa", "Belonia", "Khowai", "Bishalgarh",
    "Sonamura", "Teliamura", "Santirbazar", "Kamalpur", "Bishramganj", "Sabroom", "Melaghar",
  ],
  "Uttar Pradesh": [
    "Lucknow", "Kanpur", "Ghaziabad", "Agra", "Meerut", "Varanasi", "Prayagraj", "Bareilly", "Aligarh",
    "Moradabad", "Saharanpur", "Gorakhpur", "Noida", "Greater Noida", "Firozabad", "Jhansi", "Muzaffarnagar",
    "Mathura", "Vrindavan", "Ayodhya", "Rampur", "Shahjahanpur", "Farrukhabad", "Mau", "Hapur", "Etawah",
    "Mirzapur", "Bulandshahr", "Sambhal", "Amroha", "Hardoi", "Fatehpur", "Raebareli", "Orai", "Sitapur",
    "Bahraich", "Modinagar", "Unnao", "Jaunpur", "Lakhimpur", "Hathras", "Banda", "Pilibhit", "Barabanki",
    "Khurja", "Gonda", "Mainpuri", "Lalitpur", "Etah", "Deoria", "Ghazipur", "Sultanpur", "Azamgarh",
    "Bijnor", "Basti", "Chandausi", "Akbarpur", "Ballia", "Kasganj", "Budaun", "Kannauj", "Auraiya",
    "Mahoba", "Hamirpur", "Chitrakoot", "Manjhanpur", "Pratapgarh", "Gauriganj", "Bhinga", "Balrampur",
    "Naugarh", "Maharajganj", "Padrauna", "Khalilabad", "Bhadohi", "Gyanpur", "Chandauli", "Robertsganj",
    "Shamli", "Baghpat", "Mughalsarai", "Loni", "Muradnagar", "Tundla", "Shikohabad", "Najibabad", "Nagina",
  ],
  Uttarakhand: [
    "Dehradun", "Haridwar", "Roorkee", "Haldwani", "Rudrapur", "Kashipur", "Rishikesh", "Nainital", "Almora",
    "Pithoragarh", "Mussoorie", "Pauri", "Kotdwar", "New Tehri", "Uttarkashi", "Gopeshwar", "Rudraprayag",
    "Bageshwar", "Champawat", "Srinagar (Garhwal)", "Ramnagar", "Kichha", "Sitarganj", "Vikasnagar",
    "Joshimath",
  ],
  "West Bengal": [
    "Kolkata", "Howrah", "Durgapur", "Asansol", "Siliguri", "Bardhaman", "English Bazar (Malda)", "Kharagpur",
    "Haldia", "Baharampur", "Krishnanagar", "Barasat", "Bidhannagar", "Barrackpore", "Serampore",
    "Chinsurah", "Jalpaiguri", "Cooch Behar", "Darjeeling", "Kalimpong", "Alipurduar", "Raiganj",
    "Balurghat", "Bankura", "Purulia", "Suri", "Medinipur", "Tamluk", "Contai", "Jhargram", "Bolpur",
    "Kalyani", "Habra", "Bangaon", "Basirhat", "Diamond Harbour", "Alipore", "Uluberia", "Nabadwip",
    "Ranaghat", "Digha", "Kurseong", "Mirik", "Islampur", "Arambagh", "Katwa", "Kalna", "Raniganj", "Bally",
    "Dum Dum", "New Town",
  ],
  "Andaman and Nicobar Islands": [
    "Sri Vijaya Puram (Port Blair)", "Car Nicobar", "Mayabunder", "Diglipur", "Rangat", "Swaraj Dweep",
    "Shaheed Dweep",
  ],
  Chandigarh: ["Chandigarh"],
  "Dadra and Nagar Haveli and Daman and Diu": ["Silvassa", "Daman", "Diu"],
  Delhi: [
    "New Delhi", "Delhi", "Central Delhi", "East Delhi", "North Delhi", "North East Delhi", "North West Delhi",
    "Shahdara", "South Delhi", "South East Delhi", "South West Delhi", "West Delhi", "Dwarka", "Rohini",
    "Narela", "Najafgarh",
  ],
  "Jammu and Kashmir": [
    "Srinagar", "Jammu", "Anantnag", "Baramulla", "Sopore", "Kathua", "Udhampur", "Poonch", "Rajouri", "Doda",
    "Kishtwar", "Ramban", "Reasi", "Samba", "Kupwara", "Bandipora", "Ganderbal", "Budgam", "Pulwama",
    "Shopian", "Kulgam", "Katra", "Pahalgam", "Gulmarg",
  ],
  Ladakh: ["Leh", "Kargil", "Diskit", "Padum", "Drass"],
  Lakshadweep: ["Kavaratti", "Agatti", "Amini", "Andrott", "Minicoy", "Kalpeni", "Kadmat"],
  Puducherry: ["Puducherry", "Karaikal", "Mahe", "Yanam", "Ozhukarai"],
};

const UNION_TERRITORIES = new Set([
  "Andaman and Nicobar Islands",
  "Chandigarh",
  "Dadra and Nagar Haveli and Daman and Diu",
  "Delhi",
  "Jammu and Kashmir",
  "Ladakh",
  "Lakshadweep",
  "Puducherry",
]);

const byName = (a: string, b: string) => a.localeCompare(b, "en-IN");

/** All 28 states and 8 union territories, A–Z. */
export const INDIAN_STATES: string[] = Object.keys(CITIES_BY_STATE).sort(byName);

export const isUnionTerritory = (state: string) => UNION_TERRITORIES.has(state);

/** The canonical spelling of `state` if it's in the list (case-insensitive). */
export function findState(state: string): string | null {
  const s = state.trim().toLowerCase();
  return INDIAN_STATES.find((x) => x.toLowerCase() === s) ?? null;
}

/** Cities in `state`, A–Z. Unknown or empty state → every city in India. */
export function citiesOf(state: string): string[] {
  const key = findState(state);
  if (key) return [...new Set(CITIES_BY_STATE[key])].sort(byName);
  return [...new Set(Object.values(CITIES_BY_STATE).flat())].sort(byName);
}
