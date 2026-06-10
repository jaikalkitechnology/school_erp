/// Lightweight localization. Phase 12 will switch to ARB / flutter_intl;
/// for Phase 10 we just need English / Hindi / Marathi covered for the
/// strings the app actually shows.

enum AppLanguage { english, hindi, marathi }

extension AppLanguageX on AppLanguage {
  String get code => switch (this) {
        AppLanguage.english => 'en',
        AppLanguage.hindi => 'hi',
        AppLanguage.marathi => 'mr',
      };

  String get label => switch (this) {
        AppLanguage.english => 'English',
        AppLanguage.hindi => 'हिन्दी',
        AppLanguage.marathi => 'मराठी',
      };

  static AppLanguage fromCode(String code) => switch (code) {
        'hi' => AppLanguage.hindi,
        'mr' => AppLanguage.marathi,
        _ => AppLanguage.english,
      };
}

class AppStrings {
  const AppStrings._(this.lang);

  final AppLanguage lang;

  static AppStrings of(AppLanguage lang) => AppStrings._(lang);

  String _t(Map<AppLanguage, String> values) =>
      values[lang] ?? values[AppLanguage.english] ?? values.values.first;

  // Login screen
  String get appTagline => _t({
        AppLanguage.english: 'Your school in your pocket.',
        AppLanguage.hindi: 'आपका स्कूल आपकी जेब में।',
        AppLanguage.marathi: 'तुमचा शाळा तुमच्या खिशात.',
      });
  String get signIn => _t({
        AppLanguage.english: 'Sign in',
        AppLanguage.hindi: 'साइन इन करें',
        AppLanguage.marathi: 'साइन इन करा',
      });
  String get continueLabel => _t({
        AppLanguage.english: 'Continue',
        AppLanguage.hindi: 'जारी रखें',
        AppLanguage.marathi: 'पुढे चला',
      });
  String get signingIn => _t({
        AppLanguage.english: 'Signing in…',
        AppLanguage.hindi: 'साइन इन हो रहा है…',
        AppLanguage.marathi: 'साइन इन होत आहे…',
      });
  String get fieldRequired => _t({
        AppLanguage.english: 'Required',
        AppLanguage.hindi: 'आवश्यक',
        AppLanguage.marathi: 'आवश्यक',
      });
  String get schoolSubdomain => _t({
        AppLanguage.english: 'School subdomain',
        AppLanguage.hindi: 'स्कूल का सबडोमेन',
        AppLanguage.marathi: 'शाळेचा उपडोमेन',
      });
  String get emailOrMobile => _t({
        AppLanguage.english: 'Email or mobile',
        AppLanguage.hindi: 'ईमेल या मोबाइल',
        AppLanguage.marathi: 'ईमेल किंवा मोबाइल',
      });
  String get password => _t({
        AppLanguage.english: 'Password',
        AppLanguage.hindi: 'पासवर्ड',
        AppLanguage.marathi: 'पासवर्ड',
      });

  // Home / dashboard
  String get today => _t({
        AppLanguage.english: 'Today',
        AppLanguage.hindi: 'आज',
        AppLanguage.marathi: 'आज',
      });
  String get namaste => _t({
        AppLanguage.english: 'Namaste',
        AppLanguage.hindi: 'नमस्ते',
        AppLanguage.marathi: 'नमस्कार',
      });
  String get noChildrenLinked => _t({
        AppLanguage.english:
            'No children linked to this account yet. Ask your school admin to link them.',
        AppLanguage.hindi:
            'अभी इस खाते से कोई बच्चा नहीं जुड़ा है। स्कूल एडमिन से लिंक करवाएं।',
        AppLanguage.marathi:
            'अद्याप या खात्याशी कोणतेही मूल जोडलेले नाही. शाळा प्रशासकाला विचारा.',
      });
  String get yourSchool => _t({
        AppLanguage.english: 'Your school',
        AppLanguage.hindi: 'आपका स्कूल',
        AppLanguage.marathi: 'तुमची शाळा',
      });
  String get attendance => _t({
        AppLanguage.english: 'Attendance',
        AppLanguage.hindi: 'उपस्थिति',
        AppLanguage.marathi: 'उपस्थिती',
      });
  String get pendingLeaves => _t({
        AppLanguage.english: 'Pending leaves',
        AppLanguage.hindi: 'लंबित अवकाश',
        AppLanguage.marathi: 'प्रलंबित रजा',
      });
  String get documents => _t({
        AppLanguage.english: 'Documents',
        AppLanguage.hindi: 'दस्तावेज',
        AppLanguage.marathi: 'कागदपत्रे',
      });
  String get upcomingEvents => _t({
        AppLanguage.english: 'Upcoming events',
        AppLanguage.hindi: 'आगामी कार्यक्रम',
        AppLanguage.marathi: 'आगामी कार्यक्रम',
      });
  String get noAttendance => _t({
        AppLanguage.english: 'No attendance recorded yet.',
        AppLanguage.hindi: 'अभी कोई उपस्थिति दर्ज नहीं है।',
        AppLanguage.marathi: 'अद्याप उपस्थिती नोंदवलेली नाही.',
      });

  // Bottom nav
  String get tabHome => _t({
        AppLanguage.english: 'Home',
        AppLanguage.hindi: 'होम',
        AppLanguage.marathi: 'होम',
      });
  String get tabNotifications => _t({
        AppLanguage.english: 'Notifications',
        AppLanguage.hindi: 'सूचनाएँ',
        AppLanguage.marathi: 'सूचना',
      });
  String get tabSettings => _t({
        AppLanguage.english: 'Settings',
        AppLanguage.hindi: 'सेटिंग्स',
        AppLanguage.marathi: 'सेटिंग्ज',
      });
  String get tabAttendance => _t({
        AppLanguage.english: 'Attendance',
        AppLanguage.hindi: 'उपस्थिति',
        AppLanguage.marathi: 'उपस्थिती',
      });
  String get tabFees => _t({
        AppLanguage.english: 'Fees',
        AppLanguage.hindi: 'फीस',
        AppLanguage.marathi: 'शुल्क',
      });
  String get tabHomework => _t({
        AppLanguage.english: 'Homework',
        AppLanguage.hindi: 'गृहकार्य',
        AppLanguage.marathi: 'गृहपाठ',
      });
  String get tabMore => _t({
        AppLanguage.english: 'More',
        AppLanguage.hindi: 'और',
        AppLanguage.marathi: 'अधिक',
      });

  // Parent screens — P0 (Phases 9 / 11 / 14)
  String get attendanceMonthlyPercent => _t({
        AppLanguage.english: 'This month',
        AppLanguage.hindi: 'इस महीने',
        AppLanguage.marathi: 'या महिन्यात',
      });
  String get statusPresent => _t({
        AppLanguage.english: 'Present',
        AppLanguage.hindi: 'उपस्थित',
        AppLanguage.marathi: 'उपस्थित',
      });
  String get statusAbsent => _t({
        AppLanguage.english: 'Absent',
        AppLanguage.hindi: 'अनुपस्थित',
        AppLanguage.marathi: 'अनुपस्थित',
      });
  String get statusLate => _t({
        AppLanguage.english: 'Late',
        AppLanguage.hindi: 'देर से',
        AppLanguage.marathi: 'उशीरा',
      });
  String get statusHalfDay => _t({
        AppLanguage.english: 'Half day',
        AppLanguage.hindi: 'आधा दिन',
        AppLanguage.marathi: 'अर्धा दिवस',
      });
  String get statusLeave => _t({
        AppLanguage.english: 'On leave',
        AppLanguage.hindi: 'अवकाश',
        AppLanguage.marathi: 'रजेवर',
      });
  String get feesOutstanding => _t({
        AppLanguage.english: 'Outstanding',
        AppLanguage.hindi: 'बकाया',
        AppLanguage.marathi: 'थकीत',
      });
  String get feesPaid => _t({
        AppLanguage.english: 'Paid',
        AppLanguage.hindi: 'भुगतान किया',
        AppLanguage.marathi: 'भरलेले',
      });
  String get feesPayNow => _t({
        AppLanguage.english: 'Pay now',
        AppLanguage.hindi: 'अभी भुगतान करें',
        AppLanguage.marathi: 'आता भरा',
      });
  String get feesDueOn => _t({
        AppLanguage.english: 'Due on',
        AppLanguage.hindi: 'देय तिथि',
        AppLanguage.marathi: 'अंतिम तारीख',
      });
  String get feesNoInvoices => _t({
        AppLanguage.english: 'No fee invoices yet.',
        AppLanguage.hindi: 'अभी कोई फीस बिल नहीं है।',
        AppLanguage.marathi: 'अद्याप कोणतेही शुल्क बीजक नाही.',
      });
  String get hwOpen => _t({
        AppLanguage.english: 'Open',
        AppLanguage.hindi: 'खुला',
        AppLanguage.marathi: 'सुरू',
      });
  String get hwSubmitted => _t({
        AppLanguage.english: 'Submitted',
        AppLanguage.hindi: 'जमा किया',
        AppLanguage.marathi: 'सादर केले',
      });
  String get hwGraded => _t({
        AppLanguage.english: 'Graded',
        AppLanguage.hindi: 'जाँचा गया',
        AppLanguage.marathi: 'तपासले',
      });
  String get hwSubmitButton => _t({
        AppLanguage.english: 'Submit homework',
        AppLanguage.hindi: 'गृहकार्य जमा करें',
        AppLanguage.marathi: 'गृहपाठ सादर करा',
      });
  String get hwAnswerHint => _t({
        AppLanguage.english: 'Type the answer here…',
        AppLanguage.hindi: 'यहाँ उत्तर लिखें…',
        AppLanguage.marathi: 'येथे उत्तर लिहा…',
      });
  String get hwDueOn => _t({
        AppLanguage.english: 'Due',
        AppLanguage.hindi: 'देय',
        AppLanguage.marathi: 'अंतिम',
      });
  String get hwTeacherFeedback => _t({
        AppLanguage.english: 'Teacher feedback',
        AppLanguage.hindi: 'शिक्षक की प्रतिक्रिया',
        AppLanguage.marathi: 'शिक्षक प्रतिक्रिया',
      });
  String get hwMarks => _t({
        AppLanguage.english: 'Marks',
        AppLanguage.hindi: 'अंक',
        AppLanguage.marathi: 'गुण',
      });
  String get hwSubmitSuccess => _t({
        AppLanguage.english: 'Homework submitted.',
        AppLanguage.hindi: 'गृहकार्य जमा हो गया।',
        AppLanguage.marathi: 'गृहपाठ सादर झाला.',
      });
  String get hwSubmitFailed => _t({
        AppLanguage.english: 'Could not submit. Try again.',
        AppLanguage.hindi: 'जमा नहीं हो सका। पुनः प्रयास करें।',
        AppLanguage.marathi: 'सादर करता आले नाही. पुन्हा प्रयत्न करा.',
      });
  String get hwNoneOpen => _t({
        AppLanguage.english: 'No open homework. Nice work!',
        AppLanguage.hindi: 'कोई खुला गृहकार्य नहीं। बहुत अच्छे!',
        AppLanguage.marathi: 'कोणतेही प्रलंबित गृहपाठ नाही. छान!',
      });
  String get paymentNotConfigured => _t({
        AppLanguage.english:
            'Online payment is not yet enabled for this school. Pay at the office or via bank transfer.',
        AppLanguage.hindi:
            'इस स्कूल के लिए ऑनलाइन भुगतान अभी सक्षम नहीं है। कार्यालय में या बैंक से भुगतान करें।',
        AppLanguage.marathi:
            'या शाळेसाठी ऑनलाइन भरणा अद्याप सुरू नाही. कार्यालयात किंवा बँकेद्वारे भरा.',
      });

  // Settings
  String get language => _t({
        AppLanguage.english: 'Language',
        AppLanguage.hindi: 'भाषा',
        AppLanguage.marathi: 'भाषा',
      });
  String get appearance => _t({
        AppLanguage.english: 'Appearance',
        AppLanguage.hindi: 'थीम',
        AppLanguage.marathi: 'देखावा',
      });
  String get themeSystem => _t({
        AppLanguage.english: 'Match system',
        AppLanguage.hindi: 'सिस्टम के अनुसार',
        AppLanguage.marathi: 'सिस्टमप्रमाणे',
      });
  String get themeLight => _t({
        AppLanguage.english: 'Light',
        AppLanguage.hindi: 'लाइट',
        AppLanguage.marathi: 'फिकट',
      });
  String get themeDark => _t({
        AppLanguage.english: 'Dark',
        AppLanguage.hindi: 'डार्क',
        AppLanguage.marathi: 'गडद',
      });
  String get signOut => _t({
        AppLanguage.english: 'Sign out',
        AppLanguage.hindi: 'साइन आउट',
        AppLanguage.marathi: 'साइन आउट',
      });
  String get about => _t({
        AppLanguage.english: 'About',
        AppLanguage.hindi: 'जानकारी',
        AppLanguage.marathi: 'विषयी',
      });
  String get aboutLine => _t({
        AppLanguage.english:
            'Jaikalki School ERP · powered by Jaikalki Technology.',
        AppLanguage.hindi:
            'जयकल्की स्कूल ईआरपी · जयकल्की टेक्नोलॉजी द्वारा।',
        AppLanguage.marathi:
            'जयकल्की स्कूल ईआरपी · जयकल्की टेक्नॉलॉजीतर्फे.',
      });

  // Notifications
  String get notificationsEmpty => _t({
        AppLanguage.english: "You're all caught up.",
        AppLanguage.hindi: 'सभी सूचनाएँ देख ली गई हैं।',
        AppLanguage.marathi: 'तुम्ही सर्व सूचना पाहिल्या आहेत.',
      });
  String get networkError => _t({
        AppLanguage.english: 'Could not reach the school server.',
        AppLanguage.hindi: 'स्कूल सर्वर से कनेक्ट नहीं हो सका।',
        AppLanguage.marathi: 'शाळेच्या सर्व्हरशी कनेक्ट होऊ शकले नाही.',
      });

  // Onboarding
  List<({String title, String body})> get onboardingSlides => [
        (
          title: _t({
            AppLanguage.english: 'One login per family',
            AppLanguage.hindi: 'एक परिवार, एक लॉगिन',
            AppLanguage.marathi: 'एक कुटुंब, एक लॉगिन',
          }),
          body: _t({
            AppLanguage.english:
                'Switch between your children with one tap. Attendance, fees, homework — everything per child.',
            AppLanguage.hindi:
                'एक टैप में अपने बच्चों के बीच स्विच करें — उपस्थिति, फीस, होमवर्क।',
            AppLanguage.marathi:
                'एका टॅपमध्ये तुमच्या मुलांमध्ये स्विच करा — उपस्थिती, फी, गृहपाठ.',
          }),
        ),
        (
          title: _t({
            AppLanguage.english: 'Works offline too',
            AppLanguage.hindi: 'ऑफ़लाइन भी काम करता है',
            AppLanguage.marathi: 'ऑफलाइनही चालते',
          }),
          body: _t({
            AppLanguage.english:
                'Recently fetched data is cached on device. Critical info stays on your home screen even without signal.',
            AppLanguage.hindi:
                'हाल का डेटा डिवाइस पर सेव रहता है — बिना नेटवर्क भी ज़रूरी जानकारी मिलेगी।',
            AppLanguage.marathi:
                'अलीकडील डेटा डिव्हाइसवर साठवला जातो — नेटवर्क नसले तरी महत्त्वाची माहिती दिसते.',
          }),
        ),
        (
          title: _t({
            AppLanguage.english: 'In your language',
            AppLanguage.hindi: 'आपकी भाषा में',
            AppLanguage.marathi: 'तुमच्या भाषेत',
          }),
          body: _t({
            AppLanguage.english: 'English, हिन्दी and मराठी today. More on the way.',
            AppLanguage.hindi: 'अभी English, हिन्दी और मराठी — और आ रही हैं।',
            AppLanguage.marathi: 'सध्या English, हिन्दी आणि मराठी — आणखी येतील.',
          }),
        ),
      ];
  String get onboardingNext => _t({
        AppLanguage.english: 'Next',
        AppLanguage.hindi: 'आगे',
        AppLanguage.marathi: 'पुढे',
      });
  String get onboardingDone => _t({
        AppLanguage.english: 'Get started',
        AppLanguage.hindi: 'शुरू करें',
        AppLanguage.marathi: 'सुरुवात करा',
      });
  String get onboardingSkip => _t({
        AppLanguage.english: 'Skip',
        AppLanguage.hindi: 'छोड़ें',
        AppLanguage.marathi: 'वगळा',
      });
}
