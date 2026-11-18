/**
 * ==========================================================================
 * LEGAL RAG AI STUDIO — CLIENT CONTROLLER v3.0.0
 * Deep Onyx Obsidian • Collapsible Workspace • Floating Omnibar • Autocomplete
 * ==========================================================================
 */

window.selectedModel = 'groq';

(function () {
    'use strict';

    // ----------------------------------------------------------------------
    // 1. STATE & STORAGE KEYS
    // ----------------------------------------------------------------------
    const STORAGE_KEYS = {
        SESSIONS: 'legal_rag_sessions_v3',
        ACTIVE_SESSION_ID: 'legal_rag_active_session_id_v3',
        SIDEBAR_COLLAPSED: 'legal_rag_sidebar_collapsed_v3',
        SELECTED_MODEL: 'legal_rag_selected_model_v4'
    };

    let sessions = [];
    let activeSessionId = null;
    let isGenerating = false;
    let speechRecognitionInstance = null;
    let isListening = false;
    let attachedFiles = [];
    let indexedDocsCache = [];
    let selectedModel = 'groq';
    window.selectedModel = 'groq';

    // ======================================================================
    // COMPREHENSIVE LEGAL KNOWLEDGE BASE & AUTOCOMPLETE DICTIONARY
    // ======================================================================
    const LEGAL_KNOWLEDGE_DICTIONARY = [
        // --- CONSTITUTION OF INDIA: Fundamental Rights, DPSP, Judiciary, Executive ---
        { section: 'Preamble', title: 'Preamble of the Constitution', statute: 'Constitution', desc: 'Sovereign Socialist Secular Democratic Republic, Justice, Liberty, Equality, Fraternity' },
        { section: 'Article 1', title: 'Article 1 Constitution', statute: 'Constitution', desc: 'Name and territory of the Union (India, that is Bharat)' },
        { section: 'Article 2', title: 'Article 2 Constitution', statute: 'Constitution', desc: 'Admission or establishment of new States' },
        { section: 'Article 3', title: 'Article 3 Constitution', statute: 'Constitution', desc: 'Formation of new States and alteration of areas, boundaries or names' },
        { section: 'Article 5', title: 'Article 5 Constitution', statute: 'Constitution', desc: 'Citizenship at the commencement of the Constitution' },
        { section: 'Article 12', title: 'Article 12 Constitution', statute: 'Constitution', desc: 'Definition of "the State" for Fundamental Rights' },
        { section: 'Article 13', title: 'Article 13 Constitution', statute: 'Constitution', desc: 'Laws inconsistent with or in derogation of Fundamental Rights void (Judicial Review)' },
        { section: 'Article 14', title: 'Article 14 Constitution', statute: 'Constitution', desc: 'Equality before law & equal protection of the laws' },
        { section: 'Article 15', title: 'Article 15 Constitution', statute: 'Constitution', desc: 'Prohibition of discrimination on grounds of religion, race, caste, sex or place of birth' },
        { section: 'Article 16', title: 'Article 16 Constitution', statute: 'Constitution', desc: 'Equality of opportunity in matters of public employment & reservations' },
        { section: 'Article 17', title: 'Article 17 Constitution', statute: 'Constitution', desc: 'Abolition of Untouchability and prohibition of its practice' },
        { section: 'Article 18', title: 'Article 18 Constitution', statute: 'Constitution', desc: 'Abolition of titles except military and academic distinctions' },
        { section: 'Article 19', title: 'Article 19 Constitution', statute: 'Constitution', desc: 'Protection of 6 freedoms: speech, assembly, association, movement, residence, profession' },
        { section: 'Article 19(1)(a)', title: 'Article 19(1)(a) Constitution', statute: 'Constitution', desc: 'Freedom of speech and expression & freedom of press' },
        { section: 'Article 20', title: 'Article 20 Constitution', statute: 'Constitution', desc: 'Protection against ex-post facto laws, double jeopardy & self-incrimination' },
        { section: 'Article 21', title: 'Article 21 Constitution', statute: 'Constitution', desc: 'Protection of life and personal liberty & right to privacy (Puttaswamy)' },
        { section: 'Article 21A', title: 'Article 21A Constitution', statute: 'Constitution', desc: 'Right to free and compulsory education for children 6 to 14 years' },
        { section: 'Article 22', title: 'Article 22 Constitution', statute: 'Constitution', desc: 'Protection against arrest and detention in certain cases & preventive detention' },
        { section: 'Article 23', title: 'Article 23 Constitution', statute: 'Constitution', desc: 'Prohibition of traffic in human beings and forced labour (begar)' },
        { section: 'Article 24', title: 'Article 24 Constitution', statute: 'Constitution', desc: 'Prohibition of employment of children below 14 in factories & hazardous jobs' },
        { section: 'Article 25', title: 'Article 25 Constitution', statute: 'Constitution', desc: 'Freedom of conscience and free profession, practice and propagation of religion' },
        { section: 'Article 26', title: 'Article 26 Constitution', statute: 'Constitution', desc: 'Freedom to manage religious affairs' },
        { section: 'Article 29', title: 'Article 29 Constitution', statute: 'Constitution', desc: 'Protection of interests of minorities (language, script, culture)' },
        { section: 'Article 30', title: 'Article 30 Constitution', statute: 'Constitution', desc: 'Right of minorities to establish and administer educational institutions' },
        { section: 'Article 32', title: 'Article 32 Constitution', statute: 'Constitution', desc: 'Remedies for enforcement of Fundamental Rights (Habeas Corpus, Mandamus, Quo Warranto, Certiorari, Prohibition)' },
        { section: 'Article 36', title: 'Article 36 Constitution', statute: 'Constitution', desc: 'Definition of State for Directive Principles of State Policy (DPSP)' },
        { section: 'Article 38', title: 'Article 38 Constitution', statute: 'Constitution', desc: 'State to secure a social order for promotion of welfare of the people' },
        { section: 'Article 39', title: 'Article 39 Constitution', statute: 'Constitution', desc: 'Equal justice, free legal aid, distribution of wealth & equal pay for equal work' },
        { section: 'Article 39A', title: 'Article 39A Constitution', statute: 'Constitution', desc: 'Equal justice and free legal aid for underprivileged citizens' },
        { section: 'Article 40', title: 'Article 40 Constitution', statute: 'Constitution', desc: 'Organisation of Village Panchayats' },
        { section: 'Article 41', title: 'Article 41 Constitution', statute: 'Constitution', desc: 'Right to work, to education and to public assistance in certain cases' },
        { section: 'Article 44', title: 'Article 44 Constitution', statute: 'Constitution', desc: 'Uniform Civil Code (UCC) for citizens throughout the territory of India' },
        { section: 'Article 45', title: 'Article 45 Constitution', statute: 'Constitution', desc: 'Provision for early childhood care and education below 6 years' },
        { section: 'Article 48A', title: 'Article 48A Constitution', statute: 'Constitution', desc: 'Protection and improvement of environment and safeguarding forests and wildlife' },
        { section: 'Article 50', title: 'Article 50 Constitution', statute: 'Constitution', desc: 'Separation of Judiciary from Executive in public services' },
        { section: 'Article 51', title: 'Article 51 Constitution', statute: 'Constitution', desc: 'Promotion of international peace and security' },
        { section: 'Article 51A', title: 'Article 51A Constitution', statute: 'Constitution', desc: 'Fundamental Duties of every citizen of India' },
        { section: 'Article 52', title: 'Article 52 Constitution', statute: 'Constitution', desc: 'The President of India' },
        { section: 'Article 72', title: 'Article 72 Constitution', statute: 'Constitution', desc: 'Power of President to grant pardons, reprieves, respites or remissions' },
        { section: 'Article 74', title: 'Article 74 Constitution', statute: 'Constitution', desc: 'Council of Ministers to aid and advise President' },
        { section: 'Article 75', title: 'Article 75 Constitution', statute: 'Constitution', desc: 'Appointment of Prime Minister and Council of Ministers' },
        { section: 'Article 76', title: 'Article 76 Constitution', statute: 'Constitution', desc: 'Attorney-General for India' },
        { section: 'Article 102', title: 'Article 102 Constitution', statute: 'Constitution', desc: 'Disqualifications for membership of either House of Parliament' },
        { section: 'Article 105', title: 'Article 105 Constitution', statute: 'Constitution', desc: 'Powers, privileges and immunities of Parliament and its members' },
        { section: 'Article 123', title: 'Article 123 Constitution', statute: 'Constitution', desc: 'Power of President to promulgate Ordinances during recess of Parliament' },
        { section: 'Article 124', title: 'Article 124 Constitution', statute: 'Constitution', desc: 'Establishment and constitution of Supreme Court of India' },
        { section: 'Article 129', title: 'Article 129 Constitution', statute: 'Constitution', desc: 'Supreme Court to be a court of record & power to punish for contempt' },
        { section: 'Article 131', title: 'Article 131 Constitution', statute: 'Constitution', desc: 'Original jurisdiction of Supreme Court in Centre-State disputes' },
        { section: 'Article 136', title: 'Article 136 Constitution', statute: 'Constitution', desc: 'Special Leave Petitions (SLP) to Supreme Court' },
        { section: 'Article 141', title: 'Article 141 Constitution', statute: 'Constitution', desc: 'Law declared by Supreme Court to be binding on all courts in India' },
        { section: 'Article 142', title: 'Article 142 Constitution', statute: 'Constitution', desc: 'Enforcement of decrees and orders of Supreme Court for complete justice' },
        { section: 'Article 143', title: 'Article 143 Constitution', statute: 'Constitution', desc: 'Power of President to consult Supreme Court (Advisory Jurisdiction)' },
        { section: 'Article 161', title: 'Article 161 Constitution', statute: 'Constitution', desc: 'Power of Governor to grant pardons, reprieves or remissions' },
        { section: 'Article 163', title: 'Article 163 Constitution', statute: 'Constitution', desc: 'Council of Ministers to aid and advise Governor' },
        { section: 'Article 191', title: 'Article 191 Constitution', statute: 'Constitution', desc: 'Disqualifications for membership of State Legislative Assembly or Council' },
        { section: 'Article 213', title: 'Article 213 Constitution', statute: 'Constitution', desc: 'Power of Governor to promulgate Ordinances' },
        { section: 'Article 214', title: 'Article 214 Constitution', statute: 'Constitution', desc: 'High Courts for States' },
        { section: 'Article 215', title: 'Article 215 Constitution', statute: 'Constitution', desc: 'High Courts to be courts of record & power to punish for contempt' },
        { section: 'Article 226', title: 'Article 226 Constitution', statute: 'Constitution', desc: 'Power of High Courts to issue Writs for Fundamental Rights and any other purpose' },
        { section: 'Article 227', title: 'Article 227 Constitution', statute: 'Constitution', desc: 'Power of superintendence over all courts by the High Court' },
        { section: 'Article 246', title: 'Article 246 Constitution', statute: 'Constitution', desc: 'Subject-matter of laws made by Parliament and State Legislatures (7th Schedule)' },
        { section: 'Article 280', title: 'Article 280 Constitution', statute: 'Constitution', desc: 'Finance Commission recommendations' },
        { section: 'Article 300A', title: 'Article 300A Constitution', statute: 'Constitution', desc: 'Persons not to be deprived of property save by authority of law (Right to Property)' },
        { section: 'Article 311', title: 'Article 311 Constitution', statute: 'Constitution', desc: 'Dismissal, removal or reduction in rank of civil servants' },
        { section: 'Article 324', title: 'Article 324 Constitution', statute: 'Constitution', desc: 'Superintendence, direction and control of elections vested in Election Commission' },
        { section: 'Article 352', title: 'Article 352 Constitution', statute: 'Constitution', desc: 'Proclamation of National Emergency (War, External Aggression, Armed Rebellion)' },
        { section: 'Article 356', title: 'Article 356 Constitution', statute: 'Constitution', desc: 'President\'s Rule in States on failure of constitutional machinery' },
        { section: 'Article 360', title: 'Article 360 Constitution', statute: 'Constitution', desc: 'Provisions as to Financial Emergency' },
        { section: 'Article 368', title: 'Article 368 Constitution', statute: 'Constitution', desc: 'Power of Parliament to amend the Constitution and procedure therefor' },

        // --- BHARATIYA NYAYA SANHITA (BNS 2023) ---
        { section: 'BNS 4', title: 'Section 4 BNS', statute: 'BNS 2023', desc: 'Punishments under BNS: death, life imprisonment, rigorous/simple, forfeiture, fine, community service' },
        { section: 'BNS 14', title: 'Section 14 BNS', statute: 'BNS 2023', desc: 'Act done by a person bound or justified by law (General Exceptions)' },
        { section: 'BNS 22', title: 'Section 22 BNS', statute: 'BNS 2023', desc: 'Act of a person of unsound mind (Insanity defense)' },
        { section: 'BNS 34', title: 'Section 34 BNS', statute: 'BNS 2023', desc: 'Acts done in private defence of body or property' },
        { section: 'BNS 45', title: 'Section 45 BNS', statute: 'BNS 2023', desc: 'Abetment of an offence' },
        { section: 'BNS 61', title: 'Section 61 BNS', statute: 'BNS 2023', desc: 'Criminal conspiracy definition and punishment' },
        { section: 'BNS 63', title: 'Section 63 BNS', statute: 'BNS 2023', desc: 'Definition of rape, consent criteria, false promise of marriage & exceptions' },
        { section: 'BNS 64', title: 'Section 64 BNS', statute: 'BNS 2023', desc: 'Punishment for rape (Rigorous imprisonment 10 years to life & fine)' },
        { section: 'BNS 65', title: 'Section 65 BNS', statute: 'BNS 2023', desc: 'Punishment for rape of woman under 16 or 12 years of age' },
        { section: 'BNS 66', title: 'Section 66 BNS', statute: 'BNS 2023', desc: 'Punishment for causing death or persistent vegetative state in rape' },
        { section: 'BNS 69', title: 'Section 69 BNS', statute: 'BNS 2023', desc: 'Sexual intercourse by deceitful means or false promise to marry' },
        { section: 'BNS 70', title: 'Section 70 BNS', statute: 'BNS 2023', desc: 'Gang rape punishment (Imprisonment not less than 20 years or life)' },
        { section: 'BNS 74', title: 'Section 74 BNS', statute: 'BNS 2023', desc: 'Assault or criminal force to woman with intent to outrage modesty' },
        { section: 'BNS 78', title: 'Section 78 BNS', statute: 'BNS 2023', desc: 'Stalking definition and punishment' },
        { section: 'BNS 79', title: 'Section 79 BNS', statute: 'BNS 2023', desc: 'Word, gesture or act intended to insult modesty of a woman' },
        { section: 'BNS 80', title: 'Section 80 BNS', statute: 'BNS 2023', desc: 'Dowry death definition and punishment' },
        { section: 'BNS 85', title: 'Section 85 BNS', statute: 'BNS 2023', desc: 'Husband or relative of husband subjecting woman to cruelty' },
        { section: 'BNS 100', title: 'Section 100 BNS', statute: 'BNS 2023', desc: 'Culpable homicide defined' },
        { section: 'BNS 101', title: 'Section 101 BNS', statute: 'BNS 2023', desc: 'Murder defined' },
        { section: 'BNS 103', title: 'Section 103 BNS', statute: 'BNS 2023', desc: 'Punishment for murder (Death or life imprisonment & fine); Mob lynching clause' },
        { section: 'BNS 105', title: 'Section 105 BNS', statute: 'BNS 2023', desc: 'Punishment for culpable homicide not amounting to murder' },
        { section: 'BNS 106', title: 'Section 106 BNS', statute: 'BNS 2023', desc: 'Causing death by rash or negligent act (Hit and run provisions)' },
        { section: 'BNS 108', title: 'Section 108 BNS', statute: 'BNS 2023', desc: 'Abetment of suicide of child or person of unsound mind' },
        { section: 'BNS 109', title: 'Section 109 BNS', statute: 'BNS 2023', desc: 'Attempt to murder punishment' },
        { section: 'BNS 111', title: 'Section 111 BNS', statute: 'BNS 2023', desc: 'Organised crime definition, syndicate liability and punishment' },
        { section: 'BNS 113', title: 'Section 113 BNS', statute: 'BNS 2023', desc: 'Terrorist act definition, investigation & penalties' },
        { section: 'BNS 115', title: 'Section 115 BNS', statute: 'BNS 2023', desc: 'Voluntarily causing hurt' },
        { section: 'BNS 117', title: 'Section 117 BNS', statute: 'BNS 2023', desc: 'Voluntarily causing grievous hurt' },
        { section: 'BNS 124', title: 'Section 124 BNS', statute: 'BNS 2023', desc: 'Acid attack causing permanent injury or disfigurement' },
        { section: 'BNS 137', title: 'Section 137 BNS', statute: 'BNS 2023', desc: 'Kidnapping from India and from lawful guardianship' },
        { section: 'BNS 140', title: 'Section 140 BNS', statute: 'BNS 2023', desc: 'Kidnapping or abducting in order to murder or for ransom' },
        { section: 'BNS 143', title: 'Section 143 BNS', statute: 'BNS 2023', desc: 'Trafficking of person (Exploitation, forced labour, slavery)' },
        { section: 'BNS 152', title: 'Section 152 BNS', statute: 'BNS 2023', desc: 'Act endangering sovereignty, unity and integrity of India (Modernized replacement of Sedition)' },
        { section: 'BNS 189', title: 'Section 189 BNS', statute: 'BNS 2023', desc: 'Unlawful assembly defined and punishment' },
        { section: 'BNS 191', title: 'Section 191 BNS', statute: 'BNS 2023', desc: 'Rioting and armed rioting' },
        { section: 'BNS 303', title: 'Section 303 BNS', statute: 'BNS 2023', desc: 'Theft defined and punishment (Up to 3 years or fine/community service)' },
        { section: 'BNS 308', title: 'Section 308 BNS', statute: 'BNS 2023', desc: 'Extortion defined and punishment' },
        { section: 'BNS 309', title: 'Section 309 BNS', statute: 'BNS 2023', desc: 'Robbery defined and punishment' },
        { section: 'BNS 310', title: 'Section 310 BNS', statute: 'BNS 2023', desc: 'Dacoity defined and punishment' },
        { section: 'BNS 314', title: 'Section 314 BNS', statute: 'BNS 2023', desc: 'Dishonest misappropriation of property' },
        { section: 'BNS 316', title: 'Section 316 BNS', statute: 'BNS 2023', desc: 'Criminal breach of trust (By public servant, banker, agent)' },
        { section: 'BNS 318', title: 'Section 318 BNS', statute: 'BNS 2023', desc: 'Cheating and dishonestly inducing delivery of property (Formerly Sec 420 IPC)' },
        { section: 'BNS 324', title: 'Section 324 BNS', statute: 'BNS 2023', desc: 'Mischief and damaging public property' },
        { section: 'BNS 329', title: 'Section 329 BNS', statute: 'BNS 2023', desc: 'Criminal trespass and house-breaking' },
        { section: 'BNS 336', title: 'Section 336 BNS', statute: 'BNS 2023', desc: 'Forgery of valuable security, will or electronic record' },
        { section: 'BNS 351', title: 'Section 351 BNS', statute: 'BNS 2023', desc: 'Criminal intimidation defined and punishment' },
        { section: 'BNS 356', title: 'Section 356 BNS', statute: 'BNS 2023', desc: 'Defamation defined, exceptions and punishment (Including community service)' },

        // --- BHARATIYA NAGARIK SURAKSHA SANHITA (BNSS 2023) ---
        { section: 'BNSS 35', title: 'Section 35 BNSS', statute: 'BNSS 2023', desc: 'When police may arrest without warrant & arrest guidelines' },
        { section: 'BNSS 37', title: 'Section 37 BNSS', statute: 'BNSS 2023', desc: 'Designated Police Officer in every district and police station' },
        { section: 'BNSS 52', title: 'Section 52 BNSS', statute: 'BNSS 2023', desc: 'Examination of person accused of rape by medical practitioner' },
        { section: 'BNSS 63', title: 'Section 63 BNSS', statute: 'BNSS 2023', desc: 'Form of summons issued by court to an accused or witness' },
        { section: 'BNSS 64', title: 'Section 64 BNSS', statute: 'BNSS 2023', desc: 'Summons how served (Personal service, electronic means, SMS, email)' },
        { section: 'BNSS 70', title: 'Section 70 BNSS', statute: 'BNSS 2023', desc: 'Form of warrant of arrest and duration' },
        { section: 'BNSS 84', title: 'Section 84 BNSS', statute: 'BNSS 2023', desc: 'Proclamation for person absconding' },
        { section: 'BNSS 103', title: 'Section 103 BNSS', statute: 'BNSS 2023', desc: 'Persons in charge of closed place to allow search & ingress to police' },
        { section: 'BNSS 105', title: 'Section 105 BNSS', statute: 'BNSS 2023', desc: 'Mandatory audio-video recording of search and seizure operations' },
        { section: 'BNSS 144', title: 'Section 144 BNSS', statute: 'BNSS 2023', desc: 'Order for maintenance of wives, children and parents (Formerly Sec 125 CrPC)' },
        { section: 'BNSS 173', title: 'Section 173 BNSS', statute: 'BNSS 2023', desc: 'Information in cognizable cases (e-FIR registration, preliminary inquiry)' },
        { section: 'BNSS 175', title: 'Section 175 BNSS', statute: 'BNSS 2023', desc: 'Police officer\'s power to investigate cognizable case' },
        { section: 'BNSS 176', title: 'Section 176 BNSS', statute: 'BNSS 2023', desc: 'Procedure for investigation and mandatory forensic visit in heinous crimes' },
        { section: 'BNSS 187', title: 'Section 187 BNSS', statute: 'BNSS 2023', desc: 'Police custody and judicial custody remand procedure (15 days across 60/90 days)' },
        { section: 'BNSS 193', title: 'Section 193 BNSS', statute: 'BNSS 2023', desc: 'Report of police officer on completion of investigation (Final Charge-sheet)' },
        { section: 'BNSS 223', title: 'Section 223 BNSS', statute: 'BNSS 2023', desc: 'Examination of complainant and mandatory opportunity before taking cognizance' },
        { section: 'BNSS 356', title: 'Section 356 BNSS', statute: 'BNSS 2023', desc: 'Inquiry, trial or judgment in absentia of proclaimed offenders' },
        { section: 'BNSS 478', title: 'Section 478 BNSS', statute: 'BNSS 2023', desc: 'Bail in bailable offences' },
        { section: 'BNSS 480', title: 'Section 480 BNSS', statute: 'BNSS 2023', desc: 'When bail may be taken in non-bailable offences' },
        { section: 'BNSS 482', title: 'Section 482 BNSS', statute: 'BNSS 2023', desc: 'Direction for grant of bail to person apprehending arrest (Anticipatory Bail)' },
        { section: 'BNSS 483', title: 'Section 483 BNSS', statute: 'BNSS 2023', desc: 'Special powers of High Court or Court of Session regarding bail' },
        { section: 'BNSS 528', title: 'Section 528 BNSS', statute: 'BNSS 2023', desc: 'Saving of inherent powers of High Court to prevent abuse of process (Quashing)' },

        // --- BHARATIYA SAKSHYA ADHINIYAM (BSA 2023) ---
        { section: 'BSA 3', title: 'Section 3 BSA', statute: 'BSA 2023', desc: 'Evidence may be given of facts in issue and relevant facts' },
        { section: 'BSA 6', title: 'Section 6 BSA', statute: 'BSA 2023', desc: 'Relevancy of facts forming part of same transaction (Res Gestae)' },
        { section: 'BSA 15', title: 'Section 15 BSA', statute: 'BSA 2023', desc: 'Admission defined' },
        { section: 'BSA 22', title: 'Section 22 BSA', statute: 'BSA 2023', desc: 'Confession caused by inducement, threat or promise when irrelevant' },
        { section: 'BSA 23', title: 'Section 23 BSA', statute: 'BSA 2023', desc: 'Confession to police officer not to be proved against accused' },
        { section: 'BSA 26', title: 'Section 26 BSA', statute: 'BSA 2023', desc: 'Dying Declaration: statements by persons who cannot be called as witnesses' },
        { section: 'BSA 56', title: 'Section 56 BSA', statute: 'BSA 2023', desc: 'Proof of contents of documents (Primary or Secondary evidence)' },
        { section: 'BSA 57', title: 'Section 57 BSA', statute: 'BSA 2023', desc: 'Primary evidence defined' },
        { section: 'BSA 58', title: 'Section 58 BSA', statute: 'BSA 2023', desc: 'Secondary evidence defined' },
        { section: 'BSA 61', title: 'Section 61 BSA', statute: 'BSA 2023', desc: 'Admissibility of electronic records and digital certificates' },
        { section: 'BSA 62', title: 'Section 62 BSA', statute: 'BSA 2023', desc: 'Special provisions as to evidence relating to electronic record' },
        { section: 'BSA 63', title: 'Section 63 BSA', statute: 'BSA 2023', desc: 'Certificate for electronic record admissibility (Schedule certificate format)' },
        { section: 'BSA 103', title: 'Section 103 BSA', statute: 'BSA 2023', desc: 'Burden of proof as to particular fact' },
        { section: 'BSA 104', title: 'Section 104 BSA', statute: 'BSA 2023', desc: 'Burden of proving that case of accused comes within general exceptions' },
        { section: 'BSA 114', title: 'Section 114 BSA', statute: 'BSA 2023', desc: 'Court may presume existence of certain facts' },
        { section: 'BSA 117', title: 'Section 117 BSA', statute: 'BSA 2023', desc: 'Presumption as to dowry death' },
        { section: 'BSA 121', title: 'Section 121 BSA', statute: 'BSA 2023', desc: 'Estoppel doctrine' },
        { section: 'BSA 137', title: 'Section 137 BSA', statute: 'BSA 2023', desc: 'Examination-in-chief, cross-examination and re-examination of witnesses' },

        // --- CODE OF CIVIL PROCEDURE (CPC 1908) ---
        { section: 'CPC 9', title: 'Section 9 CPC', statute: 'Civil Procedure', desc: 'Courts to try all civil suits unless expressly or impliedly barred' },
        { section: 'CPC 10', title: 'Section 10 CPC', statute: 'Civil Procedure', desc: 'Stay of suit (Res Sub-Judice)' },
        { section: 'CPC 11', title: 'Section 11 CPC', statute: 'Civil Procedure', desc: 'Res Judicata doctrine' },
        { section: 'CPC 20', title: 'Section 20 CPC', statute: 'Civil Procedure', desc: 'Other suits to be instituted where defendants reside or cause of action arises' },
        { section: 'CPC 80', title: 'Section 80 CPC', statute: 'Civil Procedure', desc: 'Mandatory 2-month Notice before instituting suit against Government or Public Officer' },
        { section: 'CPC 89', title: 'Section 89 CPC', statute: 'Civil Procedure', desc: 'Settlement of disputes outside Court (Arbitration, Conciliation, Lok Adalat, Mediation)' },
        { section: 'CPC 96', title: 'Section 96 CPC', statute: 'Civil Procedure', desc: 'Appeal from original decree' },
        { section: 'CPC 100', title: 'Section 100 CPC', statute: 'Civil Procedure', desc: 'Second Appeal to High Court on substantial question of law' },
        { section: 'CPC 114', title: 'Section 114 CPC', statute: 'Civil Procedure', desc: 'Review of judgment by the same court' },
        { section: 'CPC 115', title: 'Section 115 CPC', statute: 'Civil Procedure', desc: 'Revision jurisdiction of High Court' },
        { section: 'CPC 151', title: 'Section 151 CPC', statute: 'Civil Procedure', desc: 'Saving of inherent powers of civil court for ends of justice' },
        { section: 'CPC Order 39', title: 'Order 39 Rules 1 & 2 CPC', statute: 'Civil Procedure', desc: 'Temporary Injunctions and interlocutory orders' },

        // --- INDIAN CONTRACT ACT 1872 ---
        { section: 'Contract 2', title: 'Section 2 Indian Contract Act', statute: 'Contracts', desc: 'Interpretation clause: proposal, promise, consideration, agreement, contract' },
        { section: 'Contract 10', title: 'Section 10 Indian Contract Act', statute: 'Contracts', desc: 'What agreements are contracts: free consent, competent parties, lawful consideration & object' },
        { section: 'Contract 11', title: 'Section 11 Indian Contract Act', statute: 'Contracts', desc: 'Who are competent to contract (Age of majority, sound mind)' },
        { section: 'Contract 14', title: 'Section 14 Indian Contract Act', statute: 'Contracts', desc: 'Free Consent defined (Absence of coercion, undue influence, fraud, misrepresentation, mistake)' },
        { section: 'Contract 15', title: 'Section 15 Indian Contract Act', statute: 'Contracts', desc: 'Coercion defined' },
        { section: 'Contract 16', title: 'Section 16 Indian Contract Act', statute: 'Contracts', desc: 'Undue Influence defined' },
        { section: 'Contract 17', title: 'Section 17 Indian Contract Act', statute: 'Contracts', desc: 'Fraud defined' },
        { section: 'Contract 18', title: 'Section 18 Indian Contract Act', statute: 'Contracts', desc: 'Misrepresentation defined' },
        { section: 'Contract 23', title: 'Section 23 Indian Contract Act', statute: 'Contracts', desc: 'What considerations and objects are lawful and what are unlawful' },
        { section: 'Contract 25', title: 'Section 25 Indian Contract Act', statute: 'Contracts', desc: 'Agreement without consideration void exceptions (Natural love, past service, time-barred debt)' },
        { section: 'Contract 27', title: 'Section 27 Indian Contract Act', statute: 'Contracts', desc: 'Agreement in restraint of trade void' },
        { section: 'Contract 28', title: 'Section 28 Indian Contract Act', statute: 'Contracts', desc: 'Agreement in restraint of legal proceedings void' },
        { section: 'Contract 56', title: 'Section 56 Indian Contract Act', statute: 'Contracts', desc: 'Agreement to do impossible act & Frustration of contract doctrine' },
        { section: 'Contract 73', title: 'Section 73 Indian Contract Act', statute: 'Contracts', desc: 'Compensation for loss or damage caused by breach of contract (Hadley v Baxendale)' },
        { section: 'Contract 74', title: 'Section 74 Indian Contract Act', statute: 'Contracts', desc: 'Compensation for breach of contract where penalty or liquidated damages stipulated' },

        // --- TRANSFER OF PROPERTY ACT 1882 ---
        { section: 'TPA 5', title: 'Section 5 Transfer of Property Act', statute: 'Property Law', desc: 'Transfer of property defined' },
        { section: 'TPA 52', title: 'Section 52 Transfer of Property Act', statute: 'Property Law', desc: 'Transfer of property pending suit relating thereto (Lis Pendens)' },
        { section: 'TPA 53', title: 'Section 53 Transfer of Property Act', statute: 'Property Law', desc: 'Fraudulent transfer of immovable property' },
        { section: 'TPA 53A', title: 'Section 53A Transfer of Property Act', statute: 'Property Law', desc: 'Part Performance doctrine' },
        { section: 'TPA 54', title: 'Section 54 Transfer of Property Act', statute: 'Property Law', desc: 'Sale defined, contract for sale and delivery of possession' },
        { section: 'TPA 58', title: 'Section 58 Transfer of Property Act', statute: 'Property Law', desc: 'Mortgage, mortgagor, mortgagee, mortgage-money and mortgage-deed defined' },
        { section: 'TPA 105', title: 'Section 105 Transfer of Property Act', statute: 'Property Law', desc: 'Lease of immovable property defined, lessor, lessee, premium and rent' },
        { section: 'TPA 122', title: 'Section 122 Transfer of Property Act', statute: 'Property Law', desc: 'Gift defined, acceptance and revocation rules' },

        // --- FAMILY, MARRIAGE & MAINTENANCE LAWS ---
        { section: 'HMA 5', title: 'Section 5 Hindu Marriage Act', statute: 'Family Law', desc: 'Conditions for a valid Hindu marriage (Monogamy, sound mind, age of majority, sapinda prohibited)' },
        { section: 'HMA 9', title: 'Section 9 Hindu Marriage Act', statute: 'Family Law', desc: 'Restitution of Conjugal Rights (RCR)' },
        { section: 'HMA 13', title: 'Section 13 Hindu Marriage Act', statute: 'Family Law', desc: 'Grounds for Divorce (Cruelty, desertion for 2 yrs, conversion, mental disorder, venereal disease)' },
        { section: 'HMA 13B', title: 'Section 13B Hindu Marriage Act', statute: 'Family Law', desc: 'Divorce by mutual consent and waiver of 6-month statutory cooling-off period' },
        { section: 'HMA 24', title: 'Section 24 Hindu Marriage Act', statute: 'Family Law', desc: 'Maintenance pendente lite and expenses of proceedings' },
        { section: 'HMA 25', title: 'Section 25 Hindu Marriage Act', statute: 'Family Law', desc: 'Permanent alimony and maintenance for spouse' },
        { section: 'SMA 4', title: 'Section 4 Special Marriage Act', statute: 'Family Law', desc: 'Conditions relating to solemnization of special marriages' },
        { section: 'SMA 28', title: 'Section 28 Special Marriage Act', statute: 'Family Law', desc: 'Divorce by mutual consent under Special Marriage Act' },
        { section: 'DV 12', title: 'Section 12 Domestic Violence Act', statute: 'Protection', desc: 'Application to Magistrate for protection orders, residence, monetary relief and compensation' },
        { section: 'DV 19', title: 'Section 19 Domestic Violence Act', statute: 'Protection', desc: 'Residence orders restraining respondent from dispossessing aggrieved person from shared household' },

        // --- COMMERCIAL, BANKING & CYBER LAWS ---
        { section: 'NI Act 138', title: 'Section 138 Negotiable Instruments Act', statute: 'Banking', desc: 'Dishonour of cheque for insufficiency of funds in accounts (Criminal cheque bounce liability)' },
        { section: 'NI Act 139', title: 'Section 139 Negotiable Instruments Act', statute: 'Banking', desc: 'Presumption in favour of holder that cheque received for discharge of debt or liability' },
        { section: 'NI Act 141', title: 'Section 141 Negotiable Instruments Act', statute: 'Banking', desc: 'Offences by companies and vicarious liability of Directors and signatories' },
        { section: 'NI Act 142', title: 'Section 142 Negotiable Instruments Act', statute: 'Banking', desc: 'Cognizance of offences under Section 138 and territorial jurisdiction' },
        { section: 'IT Act 43', title: 'Section 43 IT Act', statute: 'Cyber Law', desc: 'Penalty and compensation for damage to computer, computer system or unauthorized access' },
        { section: 'IT Act 66', title: 'Section 66 IT Act', statute: 'Cyber Law', desc: 'Computer related offences and hacking penalties' },
        { section: 'IT Act 66C', title: 'Section 66C IT Act', statute: 'Cyber Law', desc: 'Punishment for identity theft and electronic signature fraud' },
        { section: 'IT Act 66D', title: 'Section 66D IT Act', statute: 'Cyber Law', desc: 'Punishment for cheating by personation by using computer resource' },
        { section: 'IT Act 67', title: 'Section 67 IT Act', statute: 'Cyber Law', desc: 'Punishment for publishing or transmitting obscene material in electronic form' },
        { section: 'IT Act 69', title: 'Section 69 IT Act', statute: 'Cyber Law', desc: 'Power to issue directions for interception, monitoring or decryption of information' },
        { section: 'POCSO 3', title: 'Section 3 & 4 POCSO Act', statute: 'Child Protection', desc: 'Penetrative sexual assault and rigorous punishment (Up to life or death)' },
        { section: 'POCSO 5', title: 'Section 5 & 6 POCSO Act', statute: 'Child Protection', desc: 'Aggravated penetrative sexual assault and punishment' },
        { section: 'POCSO 19', title: 'Section 19 POCSO Act', statute: 'Child Protection', desc: 'Mandatory reporting of sexual offences against children to Special Juvenile Police Unit' },
        { section: 'Arbitration 8', title: 'Section 8 Arbitration Act', statute: 'Arbitration', desc: 'Power of judicial authority to refer parties to arbitration where arbitration agreement exists' },
        { section: 'Arbitration 9', title: 'Section 9 Arbitration Act', statute: 'Arbitration', desc: 'Interim measures by Court before, during or after arbitral proceedings' },
        { section: 'Arbitration 11', title: 'Section 11 Arbitration Act', statute: 'Arbitration', desc: 'Appointment of arbitrators by High Court or Supreme Court' },
        { section: 'Arbitration 34', title: 'Section 34 Arbitration Act', statute: 'Arbitration', desc: 'Application for setting aside arbitral award on grounds of patent illegality or public policy' },
        { section: 'Specific Relief 6', title: 'Section 6 Specific Relief Act', statute: 'Civil Law', desc: 'Suit by person dispossessed of immovable property without due process' },
        { section: 'Specific Relief 10', title: 'Section 10 Specific Relief Act', statute: 'Civil Law', desc: 'Mandatory specific performance of contracts' },
        { section: 'Specific Relief 34', title: 'Section 34 Specific Relief Act', statute: 'Civil Law', desc: 'Discretion of court as to declaration of status or right (Declaratory Suit)' },
        { section: 'Limitation 5', title: 'Section 5 Limitation Act', statute: 'Civil Law', desc: 'Extension of prescribed period in certain cases (Condonation of delay for sufficient cause)' }
    ];

    // ----------------------------------------------------------------------
    // 2. DOM ELEMENT REFERENCES
    // ----------------------------------------------------------------------
    const DOM = {
        appSidebar: document.getElementById('app-sidebar'),
        sidebarCollapseBtn: document.getElementById('sidebar-collapse-btn'),
        mobileSidebarBtn: document.getElementById('mobile-sidebar-btn'),
        sidebarMobileBackdrop: document.getElementById('sidebar-mobile-backdrop'),
        brandToggle: document.getElementById('brand-toggle'),
        newChatBtn: document.getElementById('new-chat-btn'),
        navChatTab: document.getElementById('nav-chat-tab'),
        navArchivedTab: document.getElementById('nav-archived-tab'),
        navLibraryTab: document.getElementById('nav-library-tab'),
        sessionsContainer: document.getElementById('sessions-container'),
        sessionsList: document.getElementById('sessions-list'),
        clearAllSessionsBtn: document.getElementById('clear-all-sessions-btn'),
        kbCard: document.getElementById('kb-card'),
        kbDocCount: document.getElementById('kb-doc-count'),
        openSettingsBtn: document.getElementById('open-settings-btn'),
        openLibraryBtn: document.getElementById('open-library-btn'),
        exportChatBtn: document.getElementById('export-chat-btn'),
        clearCurrentChatBtn: document.getElementById('clear-current-chat-btn'),
        chatContainer: document.getElementById('chat-container'),
        emptyState: document.getElementById('empty-state'),
        floatingDockWrap: document.getElementById('floating-dock-wrap'),
        dockPromptPlaceholder: document.getElementById('dock-prompt-placeholder'),
        askForm: document.getElementById('ask-form'),
        questionInput: document.getElementById('question'),
        modelSelector: document.getElementById('model-selector'),
        voiceInputBtn: document.getElementById('voice-input-btn'),
        voiceIcon: document.getElementById('voice-icon'),
        voicePulseRing: document.getElementById('voice-pulse-ring'),
        pdfInput: document.getElementById('pdf-input'),
        askButton: document.getElementById('ask-button'),
        attachedFilesBar: document.getElementById('attached-files-bar'),
        attachedFilesCount: document.getElementById('attached-files-count'),
        attachedFilesList: document.getElementById('attached-files-list'),
        uploadButton: document.getElementById('upload-button'),
        clearAttachedBtn: document.getElementById('clear-attached-btn'),
        uploadStatus: document.getElementById('upload-status'),
        autocompletePopover: document.getElementById('keyword-suggestions-popover'),
        autocompleteList: document.getElementById('keyword-suggestions-list'),
        kbModal: document.getElementById('kb-modal'),
        closeKbModalBtn: document.getElementById('close-kb-modal-btn'),
        modalTotalChunks: document.getElementById('modal-total-chunks'),
        modalTotalDocs: document.getElementById('modal-total-docs'),
        kbSearchInput: document.getElementById('kb-search-input'),
        kbDocumentsTbody: document.getElementById('kb-documents-tbody'),
        heroStatuteSub: document.getElementById('hero-statute-sub')
    };

    // ----------------------------------------------------------------------
    // 3. INITIALIZATION
    // ----------------------------------------------------------------------
    function init() {
        loadSidebarState();
        loadSessions();
        initModelSelector();
        bindEvents();
        checkBackendHealth();
        fetchDocumentStats();
        setupAutoDetectSpeechRecognition();
    }

    // ----------------------------------------------------------------------
    // 4. SIDEBAR & SESSION CONTROLS
    // ----------------------------------------------------------------------
    function loadSidebarState() {
        const collapsed = localStorage.getItem(STORAGE_KEYS.SIDEBAR_COLLAPSED) === 'true';
        if (collapsed && DOM.appSidebar) {
            DOM.appSidebar.classList.add('collapsed');
        }
    }

    function toggleSidebar() {
        if (!DOM.appSidebar) return;
        const isCollapsed = DOM.appSidebar.classList.toggle('collapsed');
        localStorage.setItem(STORAGE_KEYS.SIDEBAR_COLLAPSED, isCollapsed);
    }

    function toggleMobileSidebar() {
        if (!DOM.appSidebar) return;
        const isOpen = DOM.appSidebar.classList.toggle('mobile-open');
        if (DOM.sidebarMobileBackdrop) {
            if (isOpen) {
                DOM.sidebarMobileBackdrop.classList.remove('hidden');
            } else {
                DOM.sidebarMobileBackdrop.classList.add('hidden');
            }
        }
    }

    function closeMobileSidebar() {
        if (DOM.appSidebar && DOM.appSidebar.classList.contains('mobile-open')) {
            DOM.appSidebar.classList.remove('mobile-open');
        }
        if (DOM.sidebarMobileBackdrop) {
            DOM.sidebarMobileBackdrop.classList.add('hidden');
        }
    }

    async function loadSessions() {
        try {
            const response = await fetch('/api/sessions');
            if (response.ok) {
                sessions = await response.json();
            }
        } catch (e) {
            console.warn('Failed to load sessions from server:', e);
            sessions = [];
        }

        // Ensure each session has messages array initialized
        sessions.forEach(s => {
            if (!s.messages) s.messages = [];
            if (!s.createdAt && s.created_at) s.createdAt = s.created_at;
        });

        if (sessions.length > 0) {
            activeSessionId = sessions[0].id;
            await loadSessionMessages(activeSessionId);
        } else {
            await createNewSession(false);
        }

        renderSessionsList();
    }

    async function loadSessionMessages(sessionId) {
        activeSessionId = sessionId;
        try {
            const res = await fetch(`/api/sessions/${sessionId}/messages`);
            if (res.ok) {
                const messages = await res.json();
                const session = sessions.find(s => s.id === sessionId);
                if (session) {
                    session.messages = messages || [];
                }
            }
        } catch (e) {
            console.warn('Failed to load messages for session:', sessionId, e);
        }
        renderActiveSessionMessages();
    }

    async function createNewSession(switchToIt = true) {
        const newId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);
        const newSession = {
            id: newId,
            title: 'New Legal Query',
            createdAt: new Date().toISOString(),
            messages: []
        };
        sessions.unshift(newSession);

        try {
            await fetch('/api/sessions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: newId, title: 'New Legal Query' })
            });
        } catch (e) {
            console.warn('Error creating session on server:', e);
        }

        if (switchToIt) {
            activeSessionId = newId;
        }

        renderSessionsList();
        renderActiveSessionMessages();

        if (DOM.navChatTab) {
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            DOM.navChatTab.classList.add('active');
        }
        if (DOM.questionInput) {
            DOM.questionInput.value = '';
            autoResizeTextarea(DOM.questionInput);
            DOM.questionInput.focus();
        }
        closeMobileSidebar();
    }

    async function switchSession(sessionId) {
        if (sessionId === activeSessionId) return;
        activeSessionId = sessionId;
        await loadSessionMessages(sessionId);
        renderSessionsList();
        if (DOM.navChatTab) {
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            DOM.navChatTab.classList.add('active');
        }
        closeMobileSidebar();
    }

    async function deleteSession(sessionId, event) {
        if (event) event.stopPropagation();
        sessions = sessions.filter(s => s.id !== sessionId);

        try {
            await fetch(`/api/sessions/${sessionId}`, { method: 'DELETE' });
        } catch (e) {
            console.warn('Error deleting session on server:', e);
        }

        if (activeSessionId === sessionId) {
            activeSessionId = sessions.length > 0 ? sessions[0].id : null;
        }
        if (!activeSessionId) {
            await createNewSession(false);
        } else {
            await loadSessionMessages(activeSessionId);
        }

        renderSessionsList();
    }

    async function clearCurrentSession() {
        const session = sessions.find(s => s.id === activeSessionId);
        if (!session) return;
        session.messages = [];
        session.title = 'New Legal Query';

        try {
            await fetch(`/api/sessions/${activeSessionId}/messages`, { method: 'DELETE' });
        } catch (e) {
            console.warn('Error clearing session on server:', e);
        }

        renderSessionsList();
        renderActiveSessionMessages();
    }

    async function clearAllSessions() {
        if (!confirm('Are you sure you want to delete all saved conversations? This cannot be undone.')) {
            return;
        }
        try {
            await fetch('/api/sessions', { method: 'DELETE' });
        } catch (e) {
            console.warn('Error clearing all sessions on server:', e);
        }
        sessions = [];
        await createNewSession(true);
    }

    function renderSessionsList() {
        if (!DOM.sessionsList) return;
        const query = (DOM.sessionsSearchInput?.value || '').toLowerCase().trim();
        const filtered = sessions.filter(s => s.title.toLowerCase().includes(query));

        DOM.sessionsList.innerHTML = '';

        if (filtered.length === 0) {
            DOM.sessionsList.innerHTML = '<div style="padding: 0.75rem; font-size: 0.75rem; color: var(--text-dim); text-align: center;">No matching conversations</div>';
            return;
        }

        filtered.forEach(session => {
            const item = document.createElement('div');
            item.className = `session-item ${session.id === activeSessionId ? 'active' : ''}`;
            item.title = session.title;

            const timeStr = session.createdAt || session.created_at || new Date().toISOString();
            const timeFormatted = new Date(timeStr).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
            const count = (session.messages ? session.messages.length : (session.message_count || 0));

            item.innerHTML = `
                <span class="session-item-icon">⚖️</span>
                <div class="session-item-content">
                    <span class="session-item-title">${escapeHtml(session.title)}</span>
                    <span class="session-item-meta">${timeFormatted} • ${count} messages</span>
                </div>
                <div class="session-item-actions">
                    <button class="session-btn-action" title="Delete conversation" data-id="${session.id}">✕</button>
                </div>
            `;

            item.addEventListener('click', () => switchSession(session.id));
            const delBtn = item.querySelector('.session-btn-action');
            if (delBtn) {
                delBtn.addEventListener('click', (e) => deleteSession(session.id, e));
            }

            DOM.sessionsList.appendChild(item);
        });
    }

    // ----------------------------------------------------------------------
    // 5. CHAT VIEWPORT & MESSAGES RENDERING
    // ----------------------------------------------------------------------
    function renderActiveSessionMessages() {
        const session = sessions.find(s => s.id === activeSessionId);
        if (!session) return;

        // Clean viewport except empty-state
        const existingMessages = DOM.chatContainer.querySelectorAll('.message-row, .typing-bubble');
        existingMessages.forEach(el => el.remove());

        const promptCardWrap = document.querySelector('.zyricon-center-card-wrap');

        if (!session.messages || session.messages.length === 0) {
            if (DOM.emptyState) DOM.emptyState.classList.remove('hidden');
            if (DOM.floatingDockWrap) DOM.floatingDockWrap.classList.add('hidden');
            if (DOM.chatContainer) DOM.chatContainer.classList.remove('has-messages');
            if (promptCardWrap && DOM.emptyState) {
                const bottomGrid = DOM.emptyState.querySelector('.zyricon-bottom-grid');
                if (bottomGrid) {
                    DOM.emptyState.insertBefore(promptCardWrap, bottomGrid);
                }
            }
        } else {
            if (DOM.emptyState) DOM.emptyState.classList.add('hidden');
            if (DOM.floatingDockWrap) DOM.floatingDockWrap.classList.remove('hidden');
            if (DOM.chatContainer) DOM.chatContainer.classList.add('has-messages');
            if (promptCardWrap && DOM.dockPromptPlaceholder) {
                DOM.dockPromptPlaceholder.appendChild(promptCardWrap);
            }
            session.messages.forEach(msg => appendMessageToDOM(msg, false));
            scrollToBottom();
        }
    }

    function appendMessageToDOM(msg, scroll = true) {
        if (!DOM.chatContainer) return;
        if (DOM.emptyState) DOM.emptyState.classList.add('hidden');
        if (DOM.floatingDockWrap) DOM.floatingDockWrap.classList.remove('hidden');
        DOM.chatContainer.classList.add('has-messages');

        const promptCardWrap = document.querySelector('.zyricon-center-card-wrap');
        if (promptCardWrap && DOM.dockPromptPlaceholder && promptCardWrap.parentElement !== DOM.dockPromptPlaceholder) {
            DOM.dockPromptPlaceholder.appendChild(promptCardWrap);
        }

        const row = document.createElement('div');
        row.className = `message-row ${msg.role === 'user' ? 'user' : 'bot'}`;

        const isUser = msg.role === 'user';
        const avatarIcon = isUser ? '👤' : '⚖️';
        const roleName = isUser ? 'You' : (msg.model ? `Legal RAG AI (${getModelDisplayName(msg.model)})` : 'Legal RAG AI (Groq — Qwen 3.8 27B)');
        const timeString = msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
        const msgText = msg.text || msg.content || (msg.answer ? msg.answer : '');
        const msgCitations = msg.sources || msg.citations || msg.chunks || [];

        let sourcesHtml = '';
        if (!isUser && msgCitations && msgCitations.length > 0) {
            sourcesHtml = `
                <div class="sources-accordion">
                    <div class="sources-header">
                        <span class="sources-title">📚 Retrieved Legal Citations & Chunks (${msgCitations.length})</span>
                        <span class="sources-chevron">▼</span>
                    </div>
                    <div class="sources-body hidden">
                        ${msgCitations.map((chunk, idx) => `
                            <div class="chunk-card">
                                <div class="chunk-card-meta">
                                    <span class="chunk-doc-title">${escapeHtml(chunk.doc_name || chunk.document_name || chunk.source || chunk.act_name || `Document ${idx+1}`)}</span>
                                    <span class="chunk-score-pill">${chunk.score !== undefined ? (typeof chunk.score === 'number' && chunk.score < 1 ? `Dist: ${chunk.score.toFixed(3)}` : `Match: ${chunk.score}`) : 'ChromaDB'}</span>
                                </div>
                                <div class="chunk-snippet">${escapeHtml(chunk.text || chunk.content || chunk.snippet || '')}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        const actionsHtml = !isUser ? `
            <div class="message-actions-bar">
                <button class="btn-msg-action copy-btn" title="Copy legal answer to clipboard">
                    <span>📋 Copy</span>
                </button>
                <button class="btn-msg-action read-aloud-btn" title="Read explanation aloud">
                    <span>🔊 Speak</span>
                </button>
            </div>
        ` : '';

        row.innerHTML = `
            ${!isUser ? `<div class="message-avatar">${avatarIcon}</div>` : ''}
            <div class="message-body-wrap">
                <div class="message-meta">
                    <strong>${roleName}</strong>
                    <span>${timeString}</span>
                </div>
                <div class="message-bubble">
                    ${isUser ? `<p>${escapeHtml(msgText)}</p>` : formatMarkdown(msgText)}
                </div>
                ${sourcesHtml}
                ${actionsHtml}
            </div>
            ${isUser ? `<div class="message-avatar">${avatarIcon}</div>` : ''}
        `;

        // Wire accordion toggle
        const accordionHeader = row.querySelector('.sources-header');
        const accordionBody = row.querySelector('.sources-body');
        const accordionWrap = row.querySelector('.sources-accordion');
        if (accordionHeader && accordionBody && accordionWrap) {
            accordionHeader.addEventListener('click', () => {
                const isOpen = !accordionBody.classList.contains('hidden');
                if (isOpen) {
                    accordionBody.classList.add('hidden');
                    accordionWrap.classList.remove('open');
                } else {
                    accordionBody.classList.remove('hidden');
                    accordionWrap.classList.add('open');
                }
            });
        }

        // Wire copy button
        const copyBtn = row.querySelector('.copy-btn');
        if (copyBtn) {
            copyBtn.addEventListener('click', () => {
                navigator.clipboard.writeText(msgText).then(() => {
                    const span = copyBtn.querySelector('span');
                    if (span) {
                        const original = span.textContent;
                        span.textContent = '✓ Copied!';
                        setTimeout(() => { span.textContent = original; }, 2000);
                    }
                });
            });
        }

        // Wire TTS Read Aloud button
        const speakBtn = row.querySelector('.read-aloud-btn');
        if (speakBtn) {
            speakBtn.addEventListener('click', () => {
                speakText(msgText, speakBtn);
            });
        }

        DOM.chatContainer.appendChild(row);
        if (scroll) scrollToBottom();
    }

    function showTypingIndicator() {
        removeTypingIndicator();
        const row = document.createElement('div');
        row.id = 'typing-indicator-row';
        row.className = 'message-row bot';
        row.innerHTML = `
            <div class="message-avatar">⚖️</div>
            <div class="message-body-wrap">
                <div class="message-meta">
                    <strong>Legal RAG AI</strong>
                    <span>Analyzing Bare Acts & ChromaDB...</span>
                </div>
                <div class="typing-bubble">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        DOM.chatContainer.appendChild(row);
        scrollToBottom();
    }

    function removeTypingIndicator() {
        const el = document.getElementById('typing-indicator-row');
        if (el) el.remove();
    }

    function scrollToBottom() {
        if (DOM.chatContainer) {
            DOM.chatContainer.scrollTop = DOM.chatContainer.scrollHeight;
        }
    }

    // ----------------------------------------------------------------------
    // 6. QUESTION SUBMISSION & API CALL
    // ----------------------------------------------------------------------
    async function handleQuestionSubmit(e) {
        if (e) e.preventDefault();
        if (isGenerating) return;

        const question = DOM.questionInput.value.trim();
        if (!question) return;

        hideAutocomplete();

        const session = sessions.find(s => s.id === activeSessionId);
        if (!session) return;

        // Auto rename session title on first query
        if (session.messages.length === 0) {
            session.title = question.length > 40 ? question.substring(0, 40) + '...' : question;
            if (DOM.currentChatTitle) DOM.currentChatTitle.textContent = session.title;
            renderSessionsList();
        }

        const userMsg = {
            role: 'user',
            text: question,
            content: question,
            timestamp: new Date().toISOString()
        };
        session.messages.push(userMsg);
        appendMessageToDOM(userMsg, true);

        DOM.questionInput.value = '';
        autoResizeTextarea(DOM.questionInput);
        isGenerating = true;
        if (DOM.askButton) DOM.askButton.disabled = true;
        showTypingIndicator();

        // Format last conversation turns for contextual follow-up
        const historyPayload = (session.messages || [])
            .slice(0, -1) // exclude current message
            .slice(-8)
            .map(m => ({
                role: m.role === 'user' ? 'user' : 'assistant',
                content: m.text || m.content || ''
            }));

        const activeModel = (DOM.modelSelector && DOM.modelSelector.value) 
            ? DOM.modelSelector.value 
            : (window.selectedModel || 'groq');
        window.selectedModel = activeModel;

        const modelIdMap = {
            'groq': 'qwen/qwen3.8-27b',
            'gemini': 'gemini-flash-latest',
            'ollama': 'qwen2.5:1.5b'
        };
        const resolvedModelName = modelIdMap[activeModel] || activeModel;

        try {
            const response = await fetch('/api/ask', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: activeSessionId,
                    question: question,
                    query: question,
                    provider: activeModel,
                    model: activeModel,
                    model_name: resolvedModelName,
                    history: historyPayload
                })
            });

            removeTypingIndicator();

            if (!response.ok) {
                const errJson = await response.json().catch(() => ({}));
                throw new Error(errJson.detail || `Server responded with status ${response.status}`);
            }

            const data = await response.json();
            if (data.session_id && data.session_id !== activeSessionId) {
                session.id = data.session_id;
                activeSessionId = data.session_id;
            }
            if (session.title === 'New Legal Query' || session.title === 'New Conversation') {
                session.title = question.trim().slice(0, 40);
            }
            const botMsg = {
                role: 'bot',
                text: data.answer || data.text || 'No response generated.',
                content: data.answer || data.text || 'No response generated.',
                sources: data.sources || data.citations || data.chunks || [],
                model: activeModel,
                timestamp: new Date().toISOString()
            };

            session.messages.push(botMsg);
            appendMessageToDOM(botMsg, true);
            renderSessionsList();
        } catch (error) {
            console.error('Query execution error:', error);
            removeTypingIndicator();

            const errMsg = {
                role: 'bot',
                text: `⚠️ **Legal Query Error**: Unable to complete search.\n\n*Details:* ${error.message}\n\nPlease verify backend connectivity or try asking with specific statute names like **"Section 64 BNS"** or **"Article 44 Constitution"**.`,
                sources: [],
                timestamp: new Date().toISOString()
            };
            session.messages.push(errMsg);
            appendMessageToDOM(errMsg, true);
        } finally {
            isGenerating = false;
            if (DOM.askButton) DOM.askButton.disabled = false;
            DOM.questionInput.focus();
        }
    }

    // ----------------------------------------------------------------------
    // 7. AUTO-DETECT MULTILINGUAL SPEECH RECOGNITION
    // ----------------------------------------------------------------------
    function setupAutoDetectSpeechRecognition() {
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRec) {
            if (DOM.voiceInputBtn) {
                DOM.voiceInputBtn.title = 'Voice recognition not supported in this browser';
                DOM.voiceInputBtn.style.opacity = '0.5';
            }
            return;
        }

        try {
            speechRecognitionInstance = new SpeechRec();
            speechRecognitionInstance.continuous = false;
            speechRecognitionInstance.interimResults = true;
            speechRecognitionInstance.lang = navigator.language || 'en-IN';

            speechRecognitionInstance.onstart = () => {
                isListening = true;
                if (DOM.voiceInputBtn) DOM.voiceInputBtn.classList.add('listening');
                if (DOM.voicePulseRing) DOM.voicePulseRing.classList.remove('hidden');
                if (DOM.questionInput) DOM.questionInput.placeholder = '🎙️ Listening to your voice (English / Hindi / Hinglish)...';
            };

            speechRecognitionInstance.onresult = (event) => {
                let transcript = '';
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    transcript += event.results[i][0].transcript;
                }
                if (DOM.questionInput) {
                    DOM.questionInput.value = transcript;
                    autoResizeTextarea(DOM.questionInput);
                    handleAutocompleteInput(transcript);
                }
            };

            speechRecognitionInstance.onerror = (event) => {
                console.warn('Speech recognition event:', event.error);
                stopListening();
            };

            speechRecognitionInstance.onend = () => {
                stopListening();
            };
        } catch (err) {
            console.error('Speech recognition init error:', err);
        }
    }

    function toggleVoiceRecognition() {
        if (!speechRecognitionInstance) {
            alert('Voice input is not supported or permitted in this browser.');
            return;
        }

        if (isListening) {
            speechRecognitionInstance.stop();
            stopListening();
        } else {
            try {
                speechRecognitionInstance.start();
            } catch (e) {
                console.error('Error starting speech:', e);
                stopListening();
            }
        }
    }

    function stopListening() {
        isListening = false;
        if (DOM.voiceInputBtn) DOM.voiceInputBtn.classList.remove('listening');
        if (DOM.voicePulseRing) DOM.voicePulseRing.classList.add('hidden');
        if (DOM.questionInput) {
            DOM.questionInput.placeholder = "Ask any legal question in English, Hindi, or Hinglish (e.g., 'Section 64 of BNS' or 'Article 44')...";
        }
    }

    // ----------------------------------------------------------------------
    // 7. MULTILINGUAL ULTRA-NATURAL TEXT-TO-SPEECH (TTS)
    // ----------------------------------------------------------------------
    let currentSpeakingBtn = null;
    let availableVoices = [];
    let speechQueue = [];
    let currentChunkIndex = 0;
    let speechKeepAliveInterval = null;

    function populateVoices() {
        if ('speechSynthesis' in window) {
            availableVoices = window.speechSynthesis.getVoices() || [];
        }
    }

    if ('speechSynthesis' in window) {
        populateVoices();
        window.speechSynthesis.onvoiceschanged = populateVoices;
    }

    /**
     * Finds the highest quality, most natural neural voice for Hindi, Hinglish, or English.
     * Prevents legacy robotic SAPI voices (Kalpana, Hemant, David, Zira) from overriding
     * ultra-realistic modern voices (Swara, Madhur, Neerja, Prabhat, Google).
     */
    function findBestNaturalVoice(isHindi, isHinglish) {
        populateVoices();
        const voices = availableVoices;
        if (!voices || voices.length === 0) return null;

        if (isHindi) {
            // Pure Devanagari Hindi (हिंदी)
            // 1. Edge/Azure Online Natural Hindi Neural Voices
            const onlineNaturalHindi = voices.find(v => 
                (v.name.includes('Swara') || v.name.includes('Madhur')) && (v.name.includes('Natural') || v.name.includes('Online'))
            );
            if (onlineNaturalHindi) return onlineNaturalHindi;

            // 2. Google Hindi Voice (Chrome)
            const googleHindi = voices.find(v => 
                v.name.includes('Google') && (v.lang === 'hi-IN' || v.name.includes('हिन्दी') || v.name.includes('Hindi'))
            );
            if (googleHindi) return googleHindi;

            // 3. Any Neural/Natural Hindi Voice
            const anyNaturalHindi = voices.find(v => 
                (v.lang === 'hi-IN' || v.lang.startsWith('hi')) && (v.name.includes('Natural') || v.name.includes('Neural') || v.name.includes('Online'))
            );
            if (anyNaturalHindi) return anyNaturalHindi;

            // 4. Any modern non-Kalpana Hindi voice
            const otherHindi = voices.find(v => v.lang === 'hi-IN' && !v.name.includes('Kalpana'));
            if (otherHindi) return otherHindi;

            // 5. Fallback Hindi
            const fallbackHindi = voices.find(v => v.lang === 'hi-IN' || v.lang.startsWith('hi') || v.name.toLowerCase().includes('hindi'));
            if (fallbackHindi) return fallbackHindi;
        }

        if (isHinglish) {
            // Hinglish (Roman alphabet with Hindi legal terms, e.g. "Yeh ek bahut gambhir mamla hai...")
            // CRITICAL: Must use Indian English (en-IN) Natural voices!
            // Indian English voices naturally pronounce both English words and Romanized Hindi words
            // without spelling letters or using an awkward western/robotic accent.
            
            // 1. Edge Natural Indian English Voices (Neerja, Prabhat)
            const naturalIndianEnglish = voices.find(v => 
                (v.name.includes('Neerja') || v.name.includes('Prabhat')) && (v.name.includes('Natural') || v.name.includes('Online'))
            );
            if (naturalIndianEnglish) return naturalIndianEnglish;

            // 2. Google Indian English Voice (Chrome)
            const googleIndianEnglish = voices.find(v => 
                v.name.includes('Google') && (v.lang === 'en-IN' || v.name.includes('India'))
            );
            if (googleIndianEnglish) return googleIndianEnglish;

            // 3. Any Online Natural en-IN voice
            const anyNaturalEnIn = voices.find(v => 
                (v.lang === 'en-IN' || (v.lang.startsWith('en') && v.name.includes('India'))) && 
                (v.name.includes('Natural') || v.name.includes('Neural') || v.name.includes('Online'))
            );
            if (anyNaturalEnIn) return anyNaturalEnIn;

            // 4. Standard Indian English voices (Ravi, Heera, etc.)
            const standardEnIn = voices.find(v => v.lang === 'en-IN' || (v.name.toLowerCase().includes('india') && v.lang.startsWith('en')));
            if (standardEnIn) return standardEnIn;
        }

        // Standard English Default
        const naturalEnglish = voices.find(v => 
            (v.lang === 'en-IN' || v.name.includes('India')) && (v.name.includes('Natural') || v.name.includes('Online') || v.name.includes('Google'))
        ) || voices.find(v => 
            v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Online') || v.name.includes('Neural') || v.name.includes('Google'))
        ) || voices.find(v => v.lang === 'en-IN') || voices.find(v => v.lang.startsWith('en')) || voices[0];

        return naturalEnglish;
    }

    /**
     * Cleans and formats markdown legal text into natural, fluent speech script.
     * Expands legal acronyms (BNS -> B N S), fixes section numbers, removes code/tables/emojis,
     * and inserts clean pauses at headers and lists.
     */
    function prepareLegalTextForSpeech(text) {
        if (!text) return '';

        let clean = text;

        // 1. Remove code blocks, markdown tables, raw HTML, links
        clean = clean.replace(/```[\s\S]*?```/g, ' ');
        clean = clean.replace(/`([^`]+)`/g, '$1');
        clean = clean.replace(/https?:\/\/\S+/g, ' ');
        clean = clean.replace(/<[^>]+>/g, ' ');

        // 2. Remove emojis and UI icons
        clean = clean.replace(/[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{1F600}-\u{1F64F}\u{1F680}-\u{1F6FF}]/gu, ' ');

        // 3. Remove citations, match scores, drawer artifacts
        clean = clean.replace(/\[\s*(?:Source\s*)?\d+\s*\]/gi, ' ');
        clean = clean.replace(/Match:\s*\d+%/gi, ' ');
        clean = clean.replace(/---+\s*(?:Source|Sources)[\s\S]*?---+/gi, ' ');
        clean = clean.replace(/---+/g, '. ');

        // 4. Expand legal abbreviations to natural spoken forms
        clean = clean.replace(/\bSec\.\s*(\d+)/gi, 'Section $1');
        clean = clean.replace(/\bArt\.\s*(\d+)/gi, 'Article $1');
        clean = clean.replace(/(\b(?:Section|Article|Dhara)\s+\d+)\s*\(([a-zA-Z0-9]+)\)/gi, '$1 subsection $2');

        // Space out statutory acronyms so they are spoken crisply as letters
        clean = clean.replace(/\bBNS\b/g, 'B N S');
        clean = clean.replace(/\bBNSS\b/g, 'B N S S');
        clean = clean.replace(/\bBSA\b/g, 'B S A');
        clean = clean.replace(/\bIPC\b/g, 'I P C');
        clean = clean.replace(/\bCrPC\b/g, 'C R P C');
        clean = clean.replace(/\bCPC\b/g, 'C P C');
        clean = clean.replace(/\bFIR\b/g, 'F I R');
        clean = clean.replace(/\bUCC\b/g, 'Uniform Civil Code');
        clean = clean.replace(/\bIEA\b/g, 'I E A');
        clean = clean.replace(/\bIT\s+Act\b/gi, 'I T Act');
        clean = clean.replace(/\bv\.?\b|\bvs\.?\b/gi, 'versus');
        clean = clean.replace(/\br\/w\b/gi, 'read with');
        clean = clean.replace(/\bu\/s\b/gi, 'under section');

        // Currency
        clean = clean.replace(/\bRs\.?\s*(\d+[\d,]*)/gi, '$1 Rupees');
        clean = clean.replace(/\b₹\s*(\d+[\d,]*)/gi, '$1 Rupees');

        // 5. Structure markdown headings and lists as distinct sentences with natural pauses
        clean = clean.replace(/^#{1,6}\s*(.*)$/gm, '$1. ');
        clean = clean.replace(/^\s*[-*•]\s*(.*)$/gm, '$1. ');

        // Strip remaining markdown formatting symbols
        clean = clean.replace(/[*_~[\](){}|]/g, ' ');

        // Normalize whitespace
        clean = clean.replace(/\s+/g, ' ').trim();

        return clean;
    }

    /**
     * Splits long text into natural sentence groups of ~180-250 characters
     * to prevent Chromium Web Speech API from freezing mid-speech.
     */
    function splitTextIntoSpeechChunks(text) {
        if (!text) return [];
        // Match sentence-ending punctuation (., ?, !, ।, newlines)
        const rawSentences = text.match(/[^.!?।\n]+[.!?।\n]*/g) || [text];
        const chunks = [];
        let currentChunk = '';

        for (const raw of rawSentences) {
            const sentence = raw.trim();
            if (!sentence) continue;

            if ((currentChunk + ' ' + sentence).length > 200 && currentChunk.length > 0) {
                chunks.push(currentChunk.trim());
                currentChunk = sentence;
            } else {
                currentChunk = currentChunk ? (currentChunk + ' ' + sentence) : sentence;
            }
        }
        if (currentChunk.trim()) {
            chunks.push(currentChunk.trim());
        }
        return chunks;
    }

    function stopSpeaking() {
        if (speechKeepAliveInterval) {
            clearInterval(speechKeepAliveInterval);
            speechKeepAliveInterval = null;
        }
        speechQueue = [];
        currentChunkIndex = 0;
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
        }
        if (currentSpeakingBtn) {
            resetSpeakingBtn(currentSpeakingBtn);
            currentSpeakingBtn = null;
        }
    }

    function speakText(text, btnElement) {
        if (!('speechSynthesis' in window)) {
            alert('Text-to-speech is not supported in this browser.');
            return;
        }

        // Toggle: If currently speaking for this button, stop
        if (window.speechSynthesis.speaking && currentSpeakingBtn === btnElement) {
            stopSpeaking();
            return;
        }

        // Stop any previous speech
        stopSpeaking();

        if (!text) return;

        const clean = prepareLegalTextForSpeech(text);
        if (!clean) return;

        const hasDevanagari = /[\u0900-\u097F]/.test(clean);
        const isHinglish = !hasDevanagari && /\b(kya|hai|hain|nahi|adhiniyam|kanoon|sanhita|dharayein|dhara|ke anusar|mein|hota|hogi|hoga|diya gaya|kar sakta|kyunki|lekin|aur|parantu|saza|jurmana|zamanat|giraftari|nyayalaya|adalat|pradhan|kalam|sarkar|bhi|btao|batao|apne|apna|apni|mera|meri|mere|insaan|hatya)\b/i.test(clean);

        // Target language definition
        let targetLang = 'en-IN';
        if (hasDevanagari) {
            targetLang = 'hi-IN';
        } else if (isHinglish) {
            targetLang = 'en-IN'; // Indian English voice reads Roman Hinglish with natural Indian accent!
        } else {
            targetLang = navigator.language || 'en-IN';
        }

        const selectedVoice = findBestNaturalVoice(hasDevanagari, isHinglish);
        const chunks = splitTextIntoSpeechChunks(clean);
        if (chunks.length === 0) return;

        speechQueue = chunks;
        currentChunkIndex = 0;
        currentSpeakingBtn = btnElement;

        // Update button UI
        if (btnElement) {
            const span = btnElement.querySelector('span');
            if (span) span.textContent = '⏹️ Stop';
            btnElement.style.background = 'rgba(239, 68, 68, 0.2)';
            btnElement.style.borderColor = 'var(--red-accent)';
            btnElement.style.color = '#ffffff';
        }

        // Chrome keep-alive to prevent speech engine stall on long sentences
        speechKeepAliveInterval = setInterval(() => {
            if (window.speechSynthesis.speaking) {
                window.speechSynthesis.pause();
                window.speechSynthesis.resume();
            }
        }, 10000);

        function playNextChunk() {
            if (currentChunkIndex >= speechQueue.length) {
                stopSpeaking();
                return;
            }

            const chunkText = speechQueue[currentChunkIndex];
            const utterance = new SpeechSynthesisUtterance(chunkText);
            utterance.lang = targetLang;
            utterance.rate = 0.94; // Natural, authoritative, slightly relaxed cadence
            utterance.pitch = 1.0;

            if (selectedVoice) {
                utterance.voice = selectedVoice;
                utterance.lang = selectedVoice.lang;
            }

            utterance.onend = () => {
                currentChunkIndex++;
                if (currentChunkIndex < speechQueue.length) {
                    playNextChunk();
                } else {
                    stopSpeaking();
                }
            };

            utterance.onerror = (e) => {
                console.warn('Speech synthesis chunk error:', e);
                currentChunkIndex++;
                if (currentChunkIndex < speechQueue.length) {
                    playNextChunk();
                } else {
                    stopSpeaking();
                }
            };

            window.speechSynthesis.speak(utterance);
        }

        playNextChunk();
    }

    function resetSpeakingBtn(btn) {
        if (!btn) return;
        const span = btn.querySelector('span');
        if (span) span.textContent = '🔊 Speak';
        btn.style.background = '';
        btn.style.borderColor = '';
        btn.style.color = '';
    }

    // ----------------------------------------------------------------------
    // 8. LIVE KEYWORD & SECTION AUTOCOMPLETE
    // ----------------------------------------------------------------------
    let activeSuggestionIndex = -1;

    function handleAutocompleteInput(text) {
        if (!text || text.trim().length < 2) {
            hideAutocomplete();
            return;
        }

        const query = text.toLowerCase().trim();
        let matches = LEGAL_KNOWLEDGE_DICTIONARY.filter(item => 
            item.title.toLowerCase().includes(query) ||
            item.section.toLowerCase().includes(query) ||
            item.desc.toLowerCase().includes(query) ||
            item.statute.toLowerCase().includes(query)
        );

        const articleMatch = query.match(/^(?:article|art\.?)\s*(\d+[a-z]?)/i);
        if (articleMatch) {
            const artNum = articleMatch[1].toUpperCase();
            const exists = matches.some(m => m.section.toLowerCase().includes(`article ${artNum.toLowerCase()}`));
            if (!exists) {
                matches.unshift({
                    section: `Article ${artNum}`,
                    title: `Article ${artNum} Constitution of India`,
                    statute: 'Constitution',
                    desc: `Search provisions and Supreme Court interpretations of Article ${artNum}`
                });
            }
        }

        const sectionMatch = query.match(/^(?:section|sec\.?)\s*(\d+[a-z]?)/i);
        if (sectionMatch) {
            const secNum = sectionMatch[1].toUpperCase();
            const exists = matches.some(m => m.section.toLowerCase().includes(`bns ${secNum.toLowerCase()}`) || m.section.toLowerCase().includes(`bnss ${secNum.toLowerCase()}`));
            if (!exists) {
                matches.unshift(
                    {
                        section: `BNS ${secNum}`,
                        title: `Section ${secNum} BNS 2023`,
                        statute: 'BNS 2023',
                        desc: `Bharatiya Nyaya Sanhita substantive penal provisions for Section ${secNum}`
                    },
                    {
                        section: `BNSS ${secNum}`,
                        title: `Section ${secNum} BNSS 2023`,
                        statute: 'BNSS 2023',
                        desc: `Bharatiya Nagarik Suraksha Sanhita criminal procedure for Section ${secNum}`
                    },
                    {
                        section: `BSA ${secNum}`,
                        title: `Section ${secNum} BSA 2023`,
                        statute: 'BSA 2023',
                        desc: `Bharatiya Sakshya Adhiniyam evidence provisions for Section ${secNum}`
                    }
                );
            }
        }

        matches = matches.slice(0, 8);

        if (matches.length === 0) {
            hideAutocomplete();
            return;
        }

        activeSuggestionIndex = -1;
        DOM.autocompleteList.innerHTML = '';

        matches.forEach((item, index) => {
            const div = document.createElement('div');
            div.className = 'popover-item';
            div.dataset.index = index;
            div.innerHTML = `
                <span class="popover-badge">${escapeHtml(item.statute)}</span>
                <div class="popover-item-text">
                    <span class="popover-item-title">${escapeHtml(item.title)}</span>
                    <span class="popover-item-sub">${escapeHtml(item.desc)}</span>
                </div>
            `;

            div.addEventListener('click', () => {
                selectAutocompleteSuggestion(item.title + ' — ' + item.desc);
            });

            DOM.autocompleteList.appendChild(div);
        });

        DOM.autocompletePopover.classList.remove('hidden');
    }

    function hideAutocomplete() {
        if (DOM.autocompletePopover) {
            DOM.autocompletePopover.classList.add('hidden');
        }
        activeSuggestionIndex = -1;
    }

    function selectAutocompleteSuggestion(textToFill) {
        if (DOM.questionInput) {
            DOM.questionInput.value = textToFill;
            autoResizeTextarea(DOM.questionInput);
            DOM.questionInput.focus();
        }
        hideAutocomplete();
    }

    function handleAutocompleteKeydown(e) {
        if (!DOM.autocompletePopover || DOM.autocompletePopover.classList.contains('hidden')) return false;

        const items = DOM.autocompleteList.querySelectorAll('.popover-item');
        if (items.length === 0) return false;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            activeSuggestionIndex = (activeSuggestionIndex + 1) % items.length;
            updateActiveSuggestionUI(items);
            return true;
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            activeSuggestionIndex = (activeSuggestionIndex - 1 + items.length) % items.length;
            updateActiveSuggestionUI(items);
            return true;
        } else if (e.key === 'Tab' || (e.key === 'Enter' && activeSuggestionIndex >= 0)) {
            e.preventDefault();
            const target = items[activeSuggestionIndex >= 0 ? activeSuggestionIndex : 0];
            if (target) target.click();
            return true;
        } else if (e.key === 'Escape') {
            hideAutocomplete();
            return true;
        }
        return false;
    }

    function updateActiveSuggestionUI(items) {
        items.forEach((it, idx) => {
            if (idx === activeSuggestionIndex) {
                it.classList.add('active');
                it.scrollIntoView({ block: 'nearest' });
            } else {
                it.classList.remove('active');
            }
        });
    }

    // ----------------------------------------------------------------------
    // 9. FILE UPLOAD & KNOWLEDGE BASE DRAWER
    // ----------------------------------------------------------------------
    function handleFileSelection(e) {
        const files = Array.from(e.target.files || []);
        if (files.length === 0) return;

        attachedFiles = files;
        renderAttachedFilesBar();
    }

    function renderAttachedFilesBar() {
        if (!DOM.attachedFilesBar) return;

        if (attachedFiles.length === 0) {
            DOM.attachedFilesBar.classList.add('hidden');
            if (DOM.uploadStatus) DOM.uploadStatus.textContent = '';
            return;
        }

        DOM.attachedFilesBar.classList.remove('hidden');
        if (DOM.attachedFilesCount) {
            DOM.attachedFilesCount.textContent = `${attachedFiles.length} file(s) attached`;
        }

        if (DOM.attachedFilesList) {
            DOM.attachedFilesList.innerHTML = attachedFiles.map(f => `
                <div class="file-chip">
                    <span>📄</span>
                    <span>${escapeHtml(f.name)} (${(f.size / (1024 * 1024)).toFixed(2)} MB)</span>
                </div>
            `).join('');
        }
    }

    async function handleUploadFiles() {
        if (attachedFiles.length === 0) return;

        const formData = new FormData();
        attachedFiles.forEach(file => {
            formData.append('file', file);
            formData.append('files', file);
        });

        if (DOM.uploadButton) DOM.uploadButton.disabled = true;
        if (DOM.uploadStatus) DOM.uploadStatus.textContent = '⚡ Extracting text and generating embeddings...';

        try {
            const response = await fetch('/api/documents/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Upload failed with status ${response.status}`);
            }

            const resData = await response.json();
            if (DOM.uploadStatus) {
                DOM.uploadStatus.textContent = `✓ Successfully indexed ${attachedFiles.length} file(s)!`;
            }

            setTimeout(() => {
                attachedFiles = [];
                renderAttachedFilesBar();
                fetchDocumentStats();
            }, 2000);
        } catch (error) {
            console.error('File upload error:', error);
            if (DOM.uploadStatus) {
                DOM.uploadStatus.textContent = `❌ Upload failed: ${error.message}`;
            }
        } finally {
            if (DOM.uploadButton) DOM.uploadButton.disabled = false;
        }
    }

    async function fetchDocumentStats() {
        try {
            const response = await fetch('/api/documents/stats');
            if (!response.ok) return;
            const data = await response.json();

            const totalChunks = (typeof data.total_chunks === 'number' && data.total_chunks > 0) ? data.total_chunks : 0;
            const totalDocs = (typeof data.total_acts === 'number' && data.total_acts > 0) ? data.total_acts : ((typeof data.total_documents === 'number' && data.total_documents > 0) ? data.total_documents : 0);

            if (DOM.kbDocCount) {
                if (totalChunks > 0 && totalDocs > 0) {
                    DOM.kbDocCount.textContent = `${totalChunks.toLocaleString()} Chunks • ${totalDocs} Bare Acts indexed in ChromaDB.`;
                } else {
                    DOM.kbDocCount.textContent = `Connecting to Knowledge Base...`;
                }
            }
            if (DOM.heroStatuteSub) {
                if (totalDocs > 0 && totalChunks > 0) {
                    DOM.heroStatuteSub.textContent = `Strictly grounded in Constitution of India (106th Amendment), BNS 2023, BNSS 2023, BSA 2023, and ${totalDocs}+ Bare Acts (${totalChunks.toLocaleString()} indexed provisions).`;
                } else {
                    DOM.heroStatuteSub.textContent = `Strictly grounded in Constitution of India (106th Amendment), BNS 2023, BNSS 2023, BSA 2023, and indexed Bare Acts.`;
                }
            }
            if (DOM.modalTotalChunks && totalChunks > 0) DOM.modalTotalChunks.textContent = totalChunks.toLocaleString();
            if (DOM.modalTotalDocs && totalDocs > 0) DOM.modalTotalDocs.textContent = totalDocs.toString();

            const rawDocs = data.top_documents || data.documents || [];
            indexedDocsCache = rawDocs;
            renderDrawerDocumentsTable(indexedDocsCache);
        } catch (e) {
            console.warn('Failed to fetch document stats:', e);
        }
    }

    function renderDrawerDocumentsTable(docs) {
        if (!DOM.kbDocumentsTbody) return;
        const filter = (DOM.kbSearchInput?.value || '').toLowerCase().trim();
        const filtered = docs.filter(d => {
            const title = (d.title || d.name || d.document_name || '').toLowerCase();
            const cat = (d.category || '').toLowerCase();
            return title.includes(filter) || cat.includes(filter);
        });

        if (filtered.length === 0) {
            DOM.kbDocumentsTbody.innerHTML = `
                <tr>
                    <td colspan="5" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">
                        No indexed Acts match "${escapeHtml(filter)}"
                    </td>
                </tr>
            `;
            return;
        }

        DOM.kbDocumentsTbody.innerHTML = filtered.map(doc => {
            const title = doc.title || doc.name || doc.document_name || 'Legal Document';
            const category = doc.category || 'Bare Act';
            const pages = doc.pages || '—';
            const chunks = (doc.chunks !== undefined ? doc.chunks : (doc.chunk_count !== undefined ? doc.chunk_count : '—'));
            const formattedChunks = typeof chunks === 'number' ? chunks.toLocaleString() : chunks;

            return `
                <tr>
                    <td class="doc-name-cell">${escapeHtml(title)}</td>
                    <td><span class="doc-category-badge">${escapeHtml(category)}</span></td>
                    <td>${pages}</td>
                    <td><strong>${formattedChunks}</strong></td>
                    <td><span class="doc-status-badge">● Ready</span></td>
                </tr>
            `;
        }).join('');
    }

    function openKnowledgeBaseModal() {
        if (DOM.kbModal) {
            DOM.kbModal.classList.remove('hidden');
            fetchDocumentStats();
        }
    }

    function closeKnowledgeBaseModal() {
        if (DOM.kbModal) {
            DOM.kbModal.classList.add('hidden');
        }
    }

    // ----------------------------------------------------------------------
    // 10. SYSTEM HEALTH & EXPORT UTILITIES
    // ----------------------------------------------------------------------
    async function checkBackendHealth() {
        try {
            const res = await fetch('/api/documents/stats');
            if (res.ok) {
                if (DOM.statusDot) DOM.statusDot.style.background = 'var(--green-accent)';
                if (DOM.statusText) DOM.statusText.textContent = 'System Active & Ready';
            }
        } catch (e) {
            console.warn('Status check warning:', e);
        }
    }

    function exportChatTranscript() {
        const session = sessions.find(s => s.id === activeSessionId);
        if (!session || !session.messages || session.messages.length === 0) {
            alert('No messages to export in this conversation.');
            return;
        }

        let transcript = `# Legal RAG AI Studio — Conversation Transcript\n`;
        transcript += `**Topic:** ${session.title}\n`;
        transcript += `**Date:** ${new Date().toLocaleString()}\n`;
        transcript += `**Messages:** ${session.messages.length}\n\n---\n\n`;

        session.messages.forEach((msg) => {
            const sender = msg.role === 'user' ? '👤 User' : `⚖️ Legal RAG AI (${getModelDisplayName(msg.model)})`;
            const time = msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : '';
            transcript += `### ${sender} [${time}]\n\n${msg.text || msg.content}\n\n`;
            const msgCitations = msg.sources || msg.citations || msg.chunks || [];
            if (msgCitations && msgCitations.length > 0) {
                transcript += `**Citations:**\n`;
                msgCitations.forEach(src => {
                    transcript += `- *${src.doc_name || src.document_name || src.source || 'Doc'}*: ${src.text || src.content || src.snippet || ''}\n`;
                });
                transcript += `\n`;
            }
            transcript += `---\n\n`;
        });

        const blob = new Blob([transcript], { type: 'text/markdown;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Legal_RAG_Transcript_${Date.now()}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    function getModelDisplayName(modelKey) {
        if (!modelKey) return 'Groq — Qwen 3.8 (27B)';
        const lower = String(modelKey).toLowerCase();
        if (lower === 'groq') return 'Groq — Qwen 3.8 (27B)';
        if (lower === 'gemini') return 'Google — Gemini Flash';
        if (lower === 'ollama') return 'Ollama — Local Model';
        if (lower.includes('groq')) return 'Groq — Qwen 3.8 (27B)';
        return modelKey;
    }

    function initModelSelector() {
        const validModels = ['groq', 'gemini', 'ollama'];
        const saved = localStorage.getItem(STORAGE_KEYS.SELECTED_MODEL);
        const initialModel = (saved && validModels.includes(saved)) ? saved : 'groq';

        if (DOM.modelSelector) {
            DOM.modelSelector.value = initialModel;
        }
        selectedModel = initialModel;
        window.selectedModel = initialModel;
        localStorage.setItem(STORAGE_KEYS.SELECTED_MODEL, initialModel);

        if (DOM.modelSelector) {
            DOM.modelSelector.addEventListener('change', (e) => {
                const choice = validModels.includes(e.target.value) ? e.target.value : 'groq';
                selectedModel = choice;
                window.selectedModel = choice;
                localStorage.setItem(STORAGE_KEYS.SELECTED_MODEL, choice);
            });
        }
    }

    // ----------------------------------------------------------------------
    // 11. EVENT BINDINGS
    // ----------------------------------------------------------------------
    function bindEvents() {
        // Sidebar Toggles & Mobile Backdrop
        if (DOM.sidebarCollapseBtn) DOM.sidebarCollapseBtn.addEventListener('click', toggleSidebar);
        if (DOM.brandToggle) DOM.brandToggle.addEventListener('click', () => {
            if (DOM.appSidebar && DOM.appSidebar.classList.contains('collapsed')) {
                toggleSidebar();
            }
        });
        if (DOM.mobileSidebarBtn) DOM.mobileSidebarBtn.addEventListener('click', toggleMobileSidebar);
        if (DOM.sidebarMobileBackdrop) DOM.sidebarMobileBackdrop.addEventListener('click', closeMobileSidebar);

        if (DOM.newChatBtn) DOM.newChatBtn.addEventListener('click', () => {
            createNewSession(true);
            closeMobileSidebar();
        });
        if (DOM.sessionsSearchInput) DOM.sessionsSearchInput.addEventListener('input', renderSessionsList);

        // Sidebar Navigation Tabs
        if (DOM.navChatTab) {
            DOM.navChatTab.addEventListener('click', () => {
                document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
                DOM.navChatTab.classList.add('active');
                if (DOM.sessionsContainer) DOM.sessionsContainer.classList.add('hidden');
                closeMobileSidebar();
            });
        }

        if (DOM.navArchivedTab) {
            DOM.navArchivedTab.addEventListener('click', () => {
                document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
                DOM.navArchivedTab.classList.add('active');
                if (DOM.sessionsContainer) {
                    DOM.sessionsContainer.classList.toggle('hidden');
                    renderSessionsList();
                }
            });
        }

        if (DOM.navLibraryTab) {
            DOM.navLibraryTab.addEventListener('click', () => {
                openKnowledgeBaseModal();
                closeMobileSidebar();
            });
        }

        // Framework and Upcoming feature items
        document.querySelectorAll('.filter-trigger').forEach(trigger => {
            trigger.addEventListener('click', () => {
                const statute = trigger.dataset.statute;
                if (statute && DOM.questionInput) {
                    DOM.questionInput.value = statute;
                    autoResizeTextarea(DOM.questionInput);
                    DOM.questionInput.focus();
                    handleAutocompleteInput(statute);
                }
                closeMobileSidebar();
            });
        });

        // Top Bar Studio Controls
        if (DOM.openSettingsBtn) DOM.openSettingsBtn.addEventListener('click', openKnowledgeBaseModal);
        if (DOM.openLibraryBtn) DOM.openLibraryBtn.addEventListener('click', openKnowledgeBaseModal);
        if (DOM.kbCard) DOM.kbCard.addEventListener('click', openKnowledgeBaseModal);
        if (DOM.closeKbModalBtn) DOM.closeKbModalBtn.addEventListener('click', closeKnowledgeBaseModal);
        if (DOM.exportChatBtn) DOM.exportChatBtn.addEventListener('click', exportChatTranscript);
        if (DOM.clearCurrentChatBtn) DOM.clearCurrentChatBtn.addEventListener('click', clearCurrentSession);
        if (DOM.clearAllSessionsBtn) DOM.clearAllSessionsBtn.addEventListener('click', clearAllSessions);

        // Drawer backdrop click
        if (DOM.kbModal) {
            DOM.kbModal.addEventListener('click', (e) => {
                if (e.target === DOM.kbModal) closeKnowledgeBaseModal();
            });
        }
        if (DOM.kbSearchInput) {
            DOM.kbSearchInput.addEventListener('input', () => renderDrawerDocumentsTable(indexedDocsCache));
        }

        // Quick Statute Pill Tags
        document.querySelectorAll('.hero-tag-pill').forEach(pill => {
            pill.addEventListener('click', () => {
                const prompt = pill.dataset.prompt;
                if (prompt && DOM.questionInput) {
                    DOM.questionInput.value = prompt;
                    handleQuestionSubmit();
                }
            });
        });

        // Discovery Feature Cards (Bottom 3 Grid)
        document.querySelectorAll('.discovery-feature-card').forEach(card => {
            card.addEventListener('click', () => {
                const prompt = card.dataset.prompt;
                if (prompt && DOM.questionInput) {
                    DOM.questionInput.value = prompt;
                    handleQuestionSubmit();
                }
            });
        });

        const quickFilterBtn = document.getElementById('btn-quick-statute-filter');
        if (quickFilterBtn) {
            quickFilterBtn.addEventListener('click', () => {
                if (DOM.questionInput) {
                    DOM.questionInput.value = 'Section ';
                    DOM.questionInput.focus();
                    handleAutocompleteInput('Section');
                }
            });
        }

        // Question Form & Textarea
        if (DOM.askForm) DOM.askForm.addEventListener('submit', handleQuestionSubmit);
        if (DOM.questionInput) {
            DOM.questionInput.addEventListener('input', (e) => {
                autoResizeTextarea(e.target);
                handleAutocompleteInput(e.target.value);
            });

            DOM.questionInput.addEventListener('keydown', (e) => {
                if (handleAutocompleteKeydown(e)) return;

                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleQuestionSubmit();
                }
            });
        }

        // Voice Input Button
        if (DOM.voiceInputBtn) {
            DOM.voiceInputBtn.addEventListener('click', toggleVoiceRecognition);
        }

        // PDF Attachment & Uploading
        if (DOM.pdfInput) DOM.pdfInput.addEventListener('change', handleFileSelection);
        if (DOM.uploadButton) DOM.uploadButton.addEventListener('click', handleUploadFiles);
        if (DOM.clearAttachedBtn) {
            DOM.clearAttachedBtn.addEventListener('click', () => {
                attachedFiles = [];
                if (DOM.pdfInput) DOM.pdfInput.value = '';
                renderAttachedFilesBar();
            });
        }

        // Global Shortcuts
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
                e.preventDefault();
                createNewSession(true);
            }
            if ((e.ctrlKey || e.metaKey) && e.key === '[') {
                e.preventDefault();
                toggleSidebar();
            }
            if (e.key === 'Escape') {
                closeKnowledgeBaseModal();
                hideAutocomplete();
            }
        });

        // Hide autocomplete if clicked outside
        document.addEventListener('click', (e) => {
            if (DOM.autocompletePopover && !DOM.autocompletePopover.contains(e.target) && e.target !== DOM.questionInput) {
                hideAutocomplete();
            }
        });
    }

    // ----------------------------------------------------------------------
    // 12. HELPER UTILITIES
    // ----------------------------------------------------------------------
    function autoResizeTextarea(textarea) {
        if (!textarea) return;
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 180) + 'px';
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function formatMarkdown(text) {
        if (!text) return '';

        const lines = text.split('\n');
        const output = [];
        let inBlockquote = false;
        let blockquoteLines = [];
        let inList = null; // 'ul' or 'ol'
        let listItems = [];

        function flushBlockquote() {
            if (blockquoteLines.length > 0) {
                const content = blockquoteLines.map(l => formatInlineMarkdown(l)).join('<br>');
                output.push(`<blockquote class="legal-highlight-callout"><div class="callout-glow-bar"></div><div class="callout-inner">${content}</div></blockquote>`);
                blockquoteLines = [];
            }
            inBlockquote = false;
        }

        function flushList() {
            if (listItems.length > 0 && inList) {
                const itemsHtml = listItems.map(item => `<li>${formatInlineMarkdown(item)}</li>`).join('');
                output.push(`<${inList} class="legal-${inList}">${itemsHtml}</${inList}>`);
                listItems = [];
            }
            inList = null;
        }

        for (let i = 0; i < lines.length; i++) {
            const rawLine = lines[i];
            const trimmed = rawLine.trim();

            if (trimmed.startsWith('>')) {
                flushList();
                inBlockquote = true;
                const bqContent = trimmed.replace(/^>\s?/, '');
                blockquoteLines.push(bqContent);
                continue;
            } else if (inBlockquote) {
                flushBlockquote();
            }

            const ulMatch = trimmed.match(/^[-*•]\s+(.*)$/);
            if (ulMatch) {
                if (inList !== 'ul') {
                    flushList();
                    inList = 'ul';
                }
                listItems.push(ulMatch[1]);
                continue;
            }

            const olMatch = trimmed.match(/^(\d+)[\.\)]\s+(.*)$/);
            if (olMatch) {
                if (inList !== 'ol') {
                    flushList();
                    inList = 'ol';
                }
                listItems.push(olMatch[2]);
                continue;
            }

            if (inList) {
                flushList();
            }

            if (!trimmed) {
                continue;
            }

            if (trimmed.startsWith('### ')) {
                output.push(`<h3>${formatInlineMarkdown(trimmed.substring(4))}</h3>`);
            } else if (trimmed.startsWith('## ')) {
                output.push(`<h2>${formatInlineMarkdown(trimmed.substring(3))}</h2>`);
            } else if (trimmed.startsWith('# ')) {
                output.push(`<h1>${formatInlineMarkdown(trimmed.substring(2))}</h1>`);
            } else {
                output.push(`<p>${formatInlineMarkdown(trimmed)}</p>`);
            }
        }

        flushBlockquote();
        flushList();

        return output.join('');
    }

    function formatInlineMarkdown(str) {
        if (!str) return '';
        let escaped = escapeHtml(str);
        escaped = escaped.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        escaped = escaped.replace(/\*([^*]+)\*/g, '<em>$1</em>');
        escaped = escaped.replace(/`([^`]+)`/g, '<code>$1</code>');
        return escaped;
    }

    // Start App on DOM Ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
