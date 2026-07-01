import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("com.google.devtools.ksp")
}

val keystorePropsFile = rootProject.file("keystore.properties")
val keystoreProps = Properties()
if (keystorePropsFile.exists()) {
    keystorePropsFile.inputStream().use { keystoreProps.load(it) }
}

android {
    namespace = "ai.monster.callguard"
    compileSdk = 34

    defaultConfig {
        applicationId = "ai.monster.callguard"
        minSdk = 29
        targetSdk = 34
        versionCode = 13
        versionName = "1.3.1"
        buildConfigField("String", "THREAT_FEED_URL", "\"\"")
        buildConfigField("String", "BILLING_PRODUCT_LIFETIME", "\"monster_callguard_lifetime\"")
        buildConfigField("int", "TRIAL_DAYS", "7")
        resourceConfigurations += listOf("en", "zh-rTW")
    }

    signingConfigs {
        create("release") {
            val storePath = keystoreProps.getProperty("storeFile", "keystore/monster-callguard.jks")
            storeFile = rootProject.file(storePath)
            storePassword = keystoreProps.getProperty("storePassword", "monster-callguard-2026")
            keyAlias = keystoreProps.getProperty("keyAlias", "callguard")
            keyPassword = keystoreProps.getProperty("keyPassword", "monster-callguard-2026")
        }
    }

    buildTypes {
        debug {
            isMinifyEnabled = false
            buildConfigField("String", "THREAT_FEED_URL", "\"\"")
        }
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
            signingConfig = signingConfigs.getByName("release")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    buildFeatures {
        buildConfig = true
        compose = true
    }
    bundle {
        language { enableSplit = true }
        density { enableSplit = true }
        abi { enableSplit = true }
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("com.google.android.material:material:1.11.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-scalars:2.11.0")
    implementation("androidx.work:work-runtime-ktx:2.9.0")

    // Compose
    val composeBom = platform("androidx.compose:compose-bom:2024.02.00")
    implementation(composeBom)
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.activity:activity-compose:1.8.2")
    implementation("androidx.navigation:navigation-compose:2.7.7")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.7.0")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.7.0")
    debugImplementation("androidx.compose.ui:ui-tooling")

    // Billing — one-time purchase
    implementation("com.android.billingclient:billing-ktx:6.2.1")

    // Location + security
    implementation("com.google.android.gms:play-services-location:21.1.0")
    implementation("androidx.security:security-crypto:1.1.0-alpha06")

    // Room
    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    ksp("androidx.room:room-compiler:2.6.1")

    // International phone numbers
    implementation("com.googlecode.libphonenumber:libphonenumber:8.13.31")

    testImplementation("junit:junit:4.13.2")
    testImplementation("org.jetbrains.kotlin:kotlin-test-junit:2.0.21")
}