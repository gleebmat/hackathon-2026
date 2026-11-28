// English / German for every page. t("key", {vars}) returns the text in the chosen language; elements with
// data-i18n (text), data-i18n-html, data-i18n-ph (placeholder), data-i18n-aria and data-i18n-title are filled by
// applyStatic(). The choice is stored in localStorage ("roomv-lang"); default = the browser's language.

const DICT = {
  en: {
    // pages and header
    title_app: "Room V · Book a room", title_login: "Room V · Log in",
    brand_sub: "Find it. Book it. Study.",
    search_ph: "Search a room: 107a, Atrium, Seminarraum…", search_aria: "Search a room",
    fav_add: "Add to favourites", fav_remove: "Remove from favourites", fav_added: "{room} added to favourites",
    fav_removed: "{room} removed from favourites", favorites: "Favourite rooms", no_favs: "Tap ♥ on a room to keep it here",
    my_bookings: "My bookings", profile: "Profile", colour_theme: "Colour theme", mode: "Mode",
    mode_auto: "Auto", mode_light: "Light", mode_dark: "Dark", language: "Language", logout: "Log out",
    close: "Close", up_to_4h: "Up to 4 hours per day",
    legend_free: "Free", legend_shared: "Shared", legend_full: "Full", legend_ghost: "Ghost", legend_closed: "Closed",
    prev_month: "Previous month", next_month: "Next month", when: "When", any_time: "Any time", from: "From",
    for: "For", earlier: "Earlier", later: "Later", prev_rooms: "Previous rooms", next_rooms: "Next rooms",
    // status and purposes
    st_free: "Free", st_partial: "Shared", st_full: "Full", st_ghost: "Ghost booking", st_closed: "Closed",
    st_unbookable: "🔒 Not bookable", legend_unbookable: "Not bookable (55+ seats)",
    notes: "Notifications", notes_read_all: "Mark all as read", notes_empty: "Nothing yet. Booking reminders and sensor alerts show up here.",
    note_soon: "Your booking in {room} starts at {t}.", note_ending: "Your time in {room} ends in {m} min ({t}).",
    note_over: "Your time in {room} is over ({t}). Please leave the room as you found it.",
    note_ghost: "Nobody detected in {room}: your booking will be released at {t} unless you arrive.",
    note_released: "Your booking in {room} ({t}) was released: nobody was detected there.",
    note_booked: "Booked {room}, {day} {t}.", note_cancelled: "You cancelled your booking in {room} ({day} {t}).",
    just_now: "just now", min_ago: "{m} min ago", h_ago: "{h} h ago",
    p_quiet_study: "Quiet study", p_group_study: "Group study", p_meeting: "Meeting", p_gaming: "Gaming",
    p_board_games: "Board games", p_event: "Event", p_custom: "Other",
    noise_quiet: "quiet", noise_moderate: "moderate", noise_loud: "loud",
    exp_quiet: "Quiet expected", exp_moderate: "Moderate noise expected", exp_loud: "Loud expected",
    // days and amounts
    today: "Today", tomorrow: "Tomorrow", today_long: "Today, {d}", tomorrow_long: "Tomorrow, {d}",
    today_lower: "today", n_person: "{n} person", n_people: "{n} people", n_stars_1: "1 star", n_stars: "{n} stars",
    seats_of: "{free}/{cap} seats",
    weekdays: "Mo,Tu,We,Th,Fr,Sa,Su",
    // my bookings
    private_tag: "🔒 Private", share_tag: "👥 Open to share", cancelled: "Cancelled",
    released: "Released (nobody came)", now: "Now",
    ghost_mine: "👻 Nobody detected. Released at {t} (in {m} min) unless someone shows up.",
    day_used_up: "4 h used on this day", add_time: "+ Add time", cancel: "Cancel", sure: "Sure? Tap again",
    add_calendar: "📅 Calendar", your_rating: "Your rating", rate_room: "Rate this room",
    rated: "Thanks! You rated {room} {n}★", hours_used: "{used} of {limit} h used",
    no_upcoming: "No upcoming bookings", no_upcoming_sub: "Find a room and grab a slot.", book_a_room: "Book a room",
    history: "Past and cancelled ({n})", booking_cancelled: "Booking cancelled",
    // room sheet
    pick_day: "Pick a day", pick_time: "Pick a time", tap_start_end: "Tap a start, then an end",
    leg_shared_left: "Shared, seats left", leg_yours: "Your booking",
    left_behind: "🎒 Something left behind", left_behind_title: "Spotted by the room's camera after everyone left",
    copy_link: "🔗 Copy link", link_copied: "Link copied", right_now: "Right now",
    open_join: "open to join · ", private_dot: "private · ", until: "until {t}",
    nobody_booked: "✨ Nobody has booked it right now",
    ghost_room: "👻 Booked, but nobody is here. Frees up at {t} unless someone shows up.",
    here_one: "{n} person here now", here_many: "{n} people here now", someone_here: "Someone is here",
    nobody_here: "Nobody here", camera_unavailable: "Camera reading unavailable", board_offline: "Board offline",
    ask_ph: "Ask Room V: quiet room for 3 tomorrow at 14:00 for 2 hours", ask_aria: "Ask the room assistant", ask_btn: "Ask",
    ask_ex1: "Quiet room for 3 people tomorrow at 14:00 for 2 hours", ask_ex2: "Meeting now for 4, just us",
    ask_ex3: "Board games in Z this evening for 3h", ask_thinking: "Looking for rooms…", ask_understood: "I understood",
    ask_best: "Best rooms for that", ask_book: "Book this", ask_seats_free: "{n} seats free now", ask_live: "live sensor",
    ask_building: "Building {b}", ask_past: "That time is already over. Try a later time.",
    ask_too_far: "Bookings open at most 14 days ahead.", ask_times: "That doesn't fit the booking rules (0.5 to 4 hours, same day).",
    ask_none: "No room fits that right now. Try another time, fewer people or sharing.",
    alert_loud: "Your quiet room {room} is getting loud ({db} dB).", alert_ghost: "Nobody seen in {room}: your booking is released at {t} unless you arrive.",
    alert_left: "Something was left behind in {room}. Was it yours?", alert_open: "Open",
    board_title: "Live from the room sensor", board_people: "people in the room", board_someone: "someone is here",
    board_no_count: "no camera count yet", board_noise: "noise now", board_minute: "Noise, last minute",
    board_hw: "Camera + microphone on a XIAO ESP32S3 Sense; people counted by YOLO", board_off: "The sensor board is offline: no live readings right now.",
    here_max: "{n} here · {cap} max", booked_for_seen: "Booked for {b} · {seen}", seen_max: "{seen} · {cap} max",
    booked_for_b: "📋 Booked for <b>{b}</b>", sensor_b: "👀 Sensor: <b>{s}</b>",
    day_over: "This day is over. Pick another one.", earlier_over: "Earlier slots today are over.",
    s_free: "free", s_left: "{n} left", s_full: "full", s_closed: "closed", s_yours: "yours", s_booked: "booked",
    tap_free_slot: "Tap a free time slot to start", used_4h: "You've used your 4 h on this day. Try another day.",
    how_long: "How long", your_hours_on: "Your hours on {day}", who_join: "Who can join?",
    private_room: "Private room", private_room_sub: "Only you and your group.", open_share: "Open to share",
    open_share_sub: "Others can join until it's full.",
    only_share: "Someone already booked part of this time, so you can only share it.",
    how_many: "How many people?", seats_full: "Up to {n}, the room's limit",
    seats_share: "Up to {n} · seats still free at that time", fewer: "Fewer", more: "More", what_for: "What for?",
    custom_ph: "Describe it, e.g. Thesis writing", try_instead: "Try one of these instead:",
    booking_busy: "Booking…", book_range: "Book {a}–{b}", book: "Book",
    events_whole: "Events need the whole room", loud_then: "Someone booked a loud activity then",
    quiet_then: "Someone booked quiet study then",
    limit_reached: "You've already booked {limit} h on {day}. Pick another day.",
    booked_toast: "Booked {room}, {day} {a}–{b} 🎉",
    // search
    n_free: "{n} free", no_match: "No room matches “{q}”", no_room: "No room found",
    // picker
    closed_on: "Closed {day}", db_now: "{n} dB now", booked_out: "Booked out", no_time_left: "No free time left {day}",
    free_today: "Free time today", free_time: "Free time", h_bookable: "{h} h still bookable",
    not_available: "Not available", shared_n: "Shared · {who}", seats_left: "{n} seats left", all_seats: "All {n} seats",
    rating: "Rating", noise: "Noise", other_times: "See other times", rooms_today: "Rooms today",
    rooms_on: "Rooms on {day}", rooms_today_range: "Rooms today, {range}", rooms_on_range: "Rooms on {day}, {range}",
    t_closed: "closed",
    // login
    login_h1: "Rooms across campus,<br>free when you need them.", photo_credit: "Photo: carinthia.com",
    welcome_back: "Welcome back 👋", join: "Join Room V ✨", login_sub: "Log in with your student account.",
    tab_login: "Log in", tab_register: "Sign up", name: "Name", name_ph: "What should we call you?",
    student_email: "Student email", password: "Password", password_ph: "At least 4 characters",
    create_account: "Create account", demo_accounts: "Demo accounts (password <b>demo</b>), click to fill in:",
    // footer and help
    f_university: "University", f_aau: "AAU website", f_campus_online: "CAMPUSonline", f_moodle: "Moodle",
    f_map: "Campus map", f_support: "IT Service Desk (support)", f_how: "How it works",
    f_how_1: "Book rooms with fewer than 55 seats, up to 4 hours per day and 14 days ahead.",
    not_bookable: "Rooms with 55 or more seats (lecture halls, Aula, atrium) can't be booked here. Live status only.",
    f_how_2: "Private or open to share: shared rooms keep quiet and loud activities apart.",
    f_how_3: "Ghost bookings: if the room's sensor sees nobody, the booking is released for others.",
    f_how_4: "LIVE rooms show people, noise and things left behind, seen by the room's camera and microphone.",
    f_team: "Team", f_contact: "Questions or bugs? Write to us.", f_role_board: "Board and 3D map",
    f_role_backend: "Backend and integration", f_role_ui: "Website", f_role_models: "AI models",
    f_built: "Built at the AAU AI Hackathon 2026 · Infineon challenge", f_source: "Source code on GitHub",
    f_shortcuts: "Keyboard shortcuts", shortcuts: "Keyboard shortcuts", sc_search: "Search a room",
    sc_close: "Close the room panel or a dialog", sc_help: "Show this help", sc_lang: "Switch language",
    map_all: "All", map_all_buildings: "All buildings", map_all_floors: "All floors", map_every_floor: "Show every floor",
    map_floor: "Floor {n}", map_floor_title: "Floor {n} (floors above are hidden)",
  },
  de: {
    title_app: "Room V · Raum buchen", title_login: "Room V · Anmelden",
    brand_sub: "Finden. Buchen. Lernen.",
    search_ph: "Raum suchen: 107a, Atrium, Seminarraum…", search_aria: "Raum suchen",
    fav_add: "Zu Favoriten hinzufügen", fav_remove: "Aus Favoriten entfernen", fav_added: "{room} zu Favoriten hinzugefügt",
    fav_removed: "{room} aus Favoriten entfernt", favorites: "Lieblingsräume", no_favs: "Tippe bei einem Raum auf ♥, um ihn hier zu behalten",
    my_bookings: "Meine Buchungen", profile: "Profil", colour_theme: "Farbschema", mode: "Modus",
    mode_auto: "Auto", mode_light: "Hell", mode_dark: "Dunkel", language: "Sprache", logout: "Abmelden",
    close: "Schließen", up_to_4h: "Bis zu 4 Stunden pro Tag",
    legend_free: "Frei", legend_shared: "Geteilt", legend_full: "Voll", legend_ghost: "Geisterbuchung",
    legend_closed: "Geschlossen",
    prev_month: "Voriger Monat", next_month: "Nächster Monat", when: "Wann", any_time: "Jederzeit", from: "Ab",
    for: "Dauer", earlier: "Früher", later: "Später", prev_rooms: "Vorherige Räume", next_rooms: "Weitere Räume",
    st_free: "Frei", st_partial: "Geteilt", st_full: "Voll", st_ghost: "Geisterbuchung", st_closed: "Geschlossen",
    st_unbookable: "🔒 Nicht buchbar", legend_unbookable: "Nicht buchbar (ab 55 Plätzen)",
    notes: "Benachrichtigungen", notes_read_all: "Alle als gelesen markieren", notes_empty: "Noch nichts. Erinnerungen und Sensor-Hinweise erscheinen hier.",
    note_soon: "Deine Buchung in {room} beginnt um {t}.", note_ending: "Deine Zeit in {room} endet in {m} Min. ({t}).",
    note_over: "Deine Zeit in {room} ist vorbei ({t}). Bitte hinterlass den Raum so, wie du ihn vorgefunden hast.",
    note_ghost: "Niemand in {room} erkannt: deine Buchung wird um {t} freigegeben, wenn du nicht kommst.",
    note_released: "Deine Buchung in {room} ({t}) wurde freigegeben: dort wurde niemand erkannt.",
    note_booked: "{room} gebucht, {day} {t}.", note_cancelled: "Du hast deine Buchung in {room} storniert ({day} {t}).",
    just_now: "gerade eben", min_ago: "vor {m} Min.", h_ago: "vor {h} h",
    p_quiet_study: "Stilles Lernen", p_group_study: "Gruppenarbeit", p_meeting: "Besprechung", p_gaming: "Gaming",
    p_board_games: "Brettspiele", p_event: "Veranstaltung", p_custom: "Sonstiges",
    noise_quiet: "leise", noise_moderate: "mittel", noise_loud: "laut",
    exp_quiet: "Voraussichtlich leise", exp_moderate: "Voraussichtlich mittel", exp_loud: "Voraussichtlich laut",
    today: "Heute", tomorrow: "Morgen", today_long: "Heute, {d}", tomorrow_long: "Morgen, {d}",
    today_lower: "heute", n_person: "{n} Person", n_people: "{n} Personen", n_stars_1: "1 Stern", n_stars: "{n} Sterne",
    seats_of: "{free}/{cap} Plätze",
    weekdays: "Mo,Di,Mi,Do,Fr,Sa,So",
    private_tag: "🔒 Privat", share_tag: "👥 Zum Teilen offen", cancelled: "Storniert",
    released: "Freigegeben (niemand kam)", now: "Jetzt",
    ghost_mine: "👻 Niemand erkannt. Wird um {t} freigegeben (in {m} Min.), falls niemand kommt.",
    day_used_up: "4 h an diesem Tag verbraucht", add_time: "+ Zeit hinzufügen", cancel: "Stornieren",
    sure: "Sicher? Nochmal tippen", add_calendar: "📅 Kalender", your_rating: "Deine Bewertung",
    rate_room: "Raum bewerten", rated: "Danke! Du hast {room} mit {n}★ bewertet",
    hours_used: "{used} von {limit} h genutzt", no_upcoming: "Keine anstehenden Buchungen",
    no_upcoming_sub: "Such dir einen Raum und sichere dir einen Termin.", book_a_room: "Raum buchen",
    history: "Vergangen und storniert ({n})", booking_cancelled: "Buchung storniert",
    pick_day: "Tag wählen", pick_time: "Zeit wählen", tap_start_end: "Erst Beginn, dann Ende antippen",
    leg_shared_left: "Geteilt, Plätze frei", leg_yours: "Deine Buchung",
    left_behind: "🎒 Etwas liegen geblieben",
    left_behind_title: "Von der Raumkamera erkannt, nachdem alle gegangen sind",
    copy_link: "🔗 Link kopieren", link_copied: "Link kopiert", right_now: "Gerade jetzt",
    open_join: "offen zum Mitmachen · ", private_dot: "privat · ", until: "bis {t}",
    nobody_booked: "✨ Gerade hat ihn niemand gebucht",
    ghost_room: "👻 Gebucht, aber niemand ist da. Wird um {t} frei, falls niemand kommt.",
    here_one: "{n} Person gerade hier", here_many: "{n} Personen gerade hier", someone_here: "Jemand ist hier",
    nobody_here: "Niemand hier", camera_unavailable: "Kamerawert nicht verfügbar", board_offline: "Board offline",
    ask_ph: "Frag Room V: ruhiger Raum für 3 morgen um 14 Uhr für 2 Stunden", ask_aria: "Den Raum-Assistenten fragen", ask_btn: "Fragen",
    ask_ex1: "Ruhiger Raum für 3 Personen morgen um 14 Uhr für 2 Stunden", ask_ex2: "Besprechung jetzt zu viert, nur wir",
    ask_ex3: "Brettspiele in Z heute Abend für 3 Std", ask_thinking: "Suche Räume…", ask_understood: "Verstanden",
    ask_best: "Die besten Räume dafür", ask_book: "Diesen buchen", ask_seats_free: "{n} Plätze jetzt frei", ask_live: "Live-Sensor",
    ask_building: "Gebäude {b}", ask_past: "Diese Zeit ist schon vorbei. Versuch eine spätere.",
    ask_too_far: "Buchungen sind höchstens 14 Tage im Voraus möglich.", ask_times: "Das passt nicht zu den Buchungsregeln (0,5 bis 4 Stunden, am selben Tag).",
    ask_none: "Gerade passt kein Raum. Versuch eine andere Zeit, weniger Personen oder Teilen.",
    alert_loud: "Dein ruhiger Raum {room} wird laut ({db} dB).", alert_ghost: "Niemand in {room} gesehen: deine Buchung wird um {t} freigegeben, wenn du nicht kommst.",
    alert_left: "In {room} wurde etwas liegen gelassen. Gehört es dir?", alert_open: "Öffnen",
    board_title: "Live vom Raumsensor", board_people: "Personen im Raum", board_someone: "jemand ist da",
    board_no_count: "noch keine Kamerazählung", board_noise: "Lautstärke jetzt", board_minute: "Lautstärke, letzte Minute",
    board_hw: "Kamera + Mikrofon auf einem XIAO ESP32S3 Sense; Personen gezählt von YOLO", board_off: "Das Sensorboard ist offline: gerade keine Live-Werte.",
    here_max: "{n} hier · max. {cap}", booked_for_seen: "Gebucht für {b} · {seen}", seen_max: "{seen} · max. {cap}",
    booked_for_b: "📋 Gebucht für <b>{b}</b>", sensor_b: "👀 Sensor: <b>{s}</b>",
    day_over: "Dieser Tag ist vorbei. Wähle einen anderen.", earlier_over: "Frühere Zeiten heute sind vorbei.",
    s_free: "frei", s_left: "{n} frei", s_full: "voll", s_closed: "zu", s_yours: "deine", s_booked: "gebucht",
    tap_free_slot: "Tippe auf eine freie Zeit", used_4h: "Du hast deine 4 h an diesem Tag genutzt. Versuch einen anderen Tag.",
    how_long: "Wie lange", your_hours_on: "Deine Stunden: {day}", who_join: "Wer darf dazu?",
    private_room: "Privater Raum", private_room_sub: "Nur du und deine Gruppe.", open_share: "Zum Teilen offen",
    open_share_sub: "Andere können dazukommen, bis er voll ist.",
    only_share: "Jemand hat einen Teil dieser Zeit schon gebucht, du kannst ihn nur teilen.",
    how_many: "Wie viele Personen?", seats_full: "Bis zu {n}, das Limit des Raums",
    seats_share: "Bis zu {n} · zu der Zeit noch freie Plätze", fewer: "Weniger", more: "Mehr", what_for: "Wofür?",
    custom_ph: "Beschreib es, z. B. Masterarbeit schreiben", try_instead: "Probier stattdessen einen dieser Räume:",
    booking_busy: "Wird gebucht…", book_range: "{a}–{b} buchen", book: "Buchen",
    events_whole: "Veranstaltungen brauchen den ganzen Raum", loud_then: "Zu der Zeit ist etwas Lautes gebucht",
    quiet_then: "Zu der Zeit ist stilles Lernen gebucht",
    limit_reached: "Du hast {day} schon {limit} h gebucht. Wähle einen anderen Tag.",
    booked_toast: "{room} gebucht, {day} {a}–{b} 🎉",
    n_free: "{n} frei", no_match: "Kein Raum passt zu „{q}“", no_room: "Kein Raum gefunden",
    closed_on: "Geschlossen ({day})", db_now: "{n} dB jetzt", booked_out: "Ausgebucht",
    no_time_left: "Keine freie Zeit mehr ({day})", free_today: "Heute frei", free_time: "Freie Zeit",
    h_bookable: "Noch {h} h buchbar", not_available: "Nicht verfügbar", shared_n: "Geteilt · {who}",
    seats_left: "{n} Plätze frei", all_seats: "Alle {n} Plätze", rating: "Bewertung", noise: "Lautstärke",
    other_times: "Andere Zeiten", rooms_today: "Räume heute", rooms_on: "Räume am {day}",
    rooms_today_range: "Räume heute, {range}", rooms_on_range: "Räume am {day}, {range}", t_closed: "zu",
    login_h1: "Räume am ganzen Campus,<br>frei, wenn du sie brauchst.", photo_credit: "Foto: carinthia.com",
    welcome_back: "Willkommen zurück 👋", join: "Willkommen bei Room V ✨",
    login_sub: "Melde dich mit deinem Studierendenkonto an.",
    tab_login: "Anmelden", tab_register: "Registrieren", name: "Name", name_ph: "Wie sollen wir dich nennen?",
    student_email: "Studierenden-E-Mail", password: "Passwort", password_ph: "Mindestens 4 Zeichen",
    create_account: "Konto erstellen",
    demo_accounts: "Demo-Konten (Passwort <b>demo</b>), zum Ausfüllen anklicken:",
    f_university: "Universität", f_aau: "AAU-Website", f_campus_online: "CAMPUSonline", f_moodle: "Moodle",
    f_map: "Campusplan", f_support: "IT-Servicedesk (Support)", f_how: "So funktioniert's",
    f_how_1: "Buche Räume mit weniger als 55 Plätzen, bis zu 4 Stunden pro Tag und 14 Tage im Voraus.",
    not_bookable: "Räume ab 55 Plätzen (Hörsäle, Aula, Atrium) können hier nicht gebucht werden. Nur Live-Status.",
    f_how_2: "Privat oder geteilt: In geteilten Räumen werden leise und laute Aktivitäten getrennt.",
    f_how_3: "Geisterbuchungen: Sieht der Raumsensor niemanden, wird die Buchung für andere freigegeben.",
    f_how_4: "LIVE-Räume zeigen Personen, Lautstärke und liegen gebliebene Dinge, erfasst von Kamera und Mikrofon im Raum.",
    f_team: "Team", f_contact: "Fragen oder Fehler? Schreib uns.", f_role_board: "Board und 3D-Karte",
    f_role_backend: "Backend und Integration", f_role_ui: "Website", f_role_models: "KI-Modelle",
    f_built: "Entstanden beim AAU AI Hackathon 2026 · Infineon-Challenge", f_source: "Quellcode auf GitHub",
    f_shortcuts: "Tastenkürzel", shortcuts: "Tastenkürzel", sc_search: "Raum suchen",
    sc_close: "Raumpanel oder Dialog schließen", sc_help: "Diese Hilfe anzeigen", sc_lang: "Sprache wechseln",
    map_all: "Alle", map_all_buildings: "Alle Gebäude", map_all_floors: "Alle Etagen", map_every_floor: "Alle Etagen zeigen",
    map_floor: "Etage {n}", map_floor_title: "Etage {n} (Etagen darüber ausgeblendet)",
  },
};

// Backend errors come in English; these are translated (the rest is shown as is).
const ERRORS_DE = [
  [/^Unknown room (.+)$/, "Unbekannter Raum $1"],
  [/^Room is closed$/, "Der Raum ist geschlossen"],
  [/^Only rooms with fewer than (\d+) seats can be booked$/, "Nur Räume mit weniger als $1 Plätzen können gebucht werden"],
  [/^Room holds at most (\d+) people$/, "In den Raum passen höchstens $1 Personen"],
  [/^Room is already booked for that time$/, "Der Raum ist zu dieser Zeit schon gebucht"],
  [/^Room is booked exclusively for that time$/, "Der Raum ist zu dieser Zeit privat gebucht"],
  [/^Quiet and loud bookings can't share a room$/, "Leise und laute Buchungen können sich keinen Raum teilen"],
  [/^Room is too noisy for quiet study right now$/, "Der Raum ist gerade zu laut für stilles Lernen"],
  [/^Bookings start on the full or half hour$/, "Buchungen beginnen zur vollen oder halben Stunde"],
  [/^Book between 0.5 and 4 hours, in steps of 0.5$/, "Buche zwischen 0,5 und 4 Stunden, in Schritten von 0,5"],
  [/^Book each calendar day separately for overnight stays$/, "Über Nacht: Buche jeden Kalendertag einzeln"],
  [/^That time is in the past$/, "Diese Zeit liegt in der Vergangenheit"],
  [/^Bookings open at most (\d+) days ahead$/, "Buchungen sind höchstens $1 Tage im Voraus möglich"],
  [/^Events need the whole room$/, "Veranstaltungen brauchen den ganzen Raum"],
  [/^Describe the purpose$/, "Beschreib den Zweck"],
  [/^You already have a booking at that time$/, "Du hast zu dieser Zeit schon eine Buchung"],
  [/^Daily limit is (\S+) h; you have (\S+) h left on (\S+)$/, "Tageslimit ist $1 h; am $3 hast du noch $2 h"],
  [/^You can rate a room after you have used it$/, "Du kannst einen Raum bewerten, nachdem du ihn genutzt hast"],
  [/^Not logged in$/, "Nicht angemeldet"],
  [/^Use your student email \((.+)\)$/, "Verwende deine Studierenden-E-Mail ($1)"],
  [/^Password needs at least (\d+) characters$/, "Das Passwort braucht mindestens $1 Zeichen"],
  [/^An account with this email already exists$/, "Es gibt schon ein Konto mit dieser E-Mail"],
  [/^Wrong email or password$/, "Falsche E-Mail oder falsches Passwort"],
  [/^No active booking with that id$/, "Keine aktive Buchung mit dieser Nummer"],
  [/^This booking is already over$/, "Diese Buchung ist schon vorbei"],
  [/^Can't reach the server\. Is the backend running\?$/, "Server nicht erreichbar. Läuft das Backend?"],
];

function stored() {
  try { return localStorage.getItem("roomv-lang"); } catch { return null; }
}

export const lang = DICT[stored()] ? stored() : (navigator.language || "").toLowerCase().startsWith("de") ? "de" : "en";
export const locale = lang === "de" ? "de-AT" : "en-GB";
document.documentElement.lang = lang;

export function t(key, vars = {}) {
  const text = DICT[lang][key] ?? DICT.en[key] ?? key;
  return text.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? vars[k] : m));   // unknown {x} stays for later
}

/** "1 person" / "3 people" in the current language. */
export const people = (n) => t(n === 1 ? "n_person" : "n_people", { n });

// Room types come in English from the room data (web/map3d/campus.json).
const ROOM_TYPES_DE = { "Seminar room": "Seminarraum", "Lecture hall": "Hörsaal", "Event hall": "Veranstaltungssaal" };
export const tRoom = (name) => (lang === "de" && ROOM_TYPES_DE[name]) || name;

export function tError(message) {
  if (lang !== "de" || !message) return message;
  for (const [re, de] of ERRORS_DE) if (re.test(message)) return message.replace(re, de);
  return message;
}

export function applyStatic(root = document) {
  for (const el of root.querySelectorAll("[data-i18n]")) el.textContent = t(el.dataset.i18n);
  for (const el of root.querySelectorAll("[data-i18n-html]")) el.innerHTML = t(el.dataset.i18nHtml);
  for (const el of root.querySelectorAll("[data-i18n-ph]")) el.placeholder = t(el.dataset.i18nPh);
  for (const el of root.querySelectorAll("[data-i18n-aria]")) el.setAttribute("aria-label", t(el.dataset.i18nAria));
  for (const el of root.querySelectorAll("[data-i18n-title]")) el.title = t(el.dataset.i18nTitle);
}

export function setLang(next) {
  try { localStorage.setItem("roomv-lang", next); } catch { /* private mode: only this page load */ }
  location.reload();
}

/** EN | DE buttons inside el; clicking one switches the whole site. */
export function langSwitch(el) {
  el.innerHTML = ["en", "de"].map((l) => `<button type="button" data-lang="${l}" class="${l === lang ? "active" : ""}"
    aria-pressed="${l === lang}">${l.toUpperCase()}</button>`).join("");
  el.addEventListener("click", (e) => {
    const b = e.target.closest("[data-lang]");
    if (b && b.dataset.lang !== lang) setLang(b.dataset.lang);
  });
}
