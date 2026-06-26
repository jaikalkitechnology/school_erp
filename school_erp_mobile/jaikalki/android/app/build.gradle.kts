plugins {
    id("com.android.application")
    id("kotlin-android")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
    // Wire the google-services.json the user dropped in app/. Without this
    // plugin the JSON is ignored at build time and Firebase init fails on
    // the device with "Default FirebaseApp is not initialized".
    id("com.google.gms.google-services")
}

android {
    namespace = "com.jaikalki.school_erp"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
        // flutter_local_notifications needs Java 8+ APIs on older Android
        // levels (Optional, Stream, etc.). Desugaring backports them to the
        // app's minSdk.
        isCoreLibraryDesugaringEnabled = true
    }

    kotlinOptions {
        jvmTarget = JavaVersion.VERSION_17.toString()
    }

    defaultConfig {
        // TODO: Specify your own unique Application ID (https://developer.android.com/studio/build/application-id.html).
        applicationId = "com.jaikalki.school_erp"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
        // multiDex is required when desugaring is on with minSdk < 21.
        multiDexEnabled = true

        // Resolves the ${MAPS_API_KEY} placeholder in AndroidManifest.xml.
        // Override by passing -PMAPS_API_KEY=AIza... to gradle, or by
        // adding `MAPS_API_KEY=AIza...` to ~/.gradle/gradle.properties.
        // Without a real key the map renders a blank gray canvas with
        // "For development purposes only" — Maps SDK won't draw tiles.
        manifestPlaceholders["MAPS_API_KEY"] =
            (project.findProperty("MAPS_API_KEY") as String?) ?: "PASTE_GOOGLE_MAPS_KEY_HERE"
    }

    buildTypes {
        release {
            // TODO: Add your own signing config for the release build.
            // Signing with the debug keys for now, so `flutter run --release` works.
            signingConfig = signingConfigs.getByName("debug")
        }
    }
}

dependencies {
    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.5")
}

flutter {
    source = "../.."
}
