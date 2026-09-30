allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

val newBuildDir: Directory =
    rootProject.layout.buildDirectory
        .dir("../../build")
        .get()
rootProject.layout.buildDirectory.value(newBuildDir)

subprojects {
    val newSubprojectBuildDir: Directory = newBuildDir.dir(project.name)
    project.layout.buildDirectory.value(newSubprojectBuildDir)
}
// app_settings 5.2.0 compila contra android-33, pero sus dependencias AndroidX
// exigen 34 o superior. Se sube el compileSdk de los plugins atrasados sin
// cambiar su minSdk ni el targetSdk de la app. Retirar al actualizar el plugin.
subprojects {
    afterEvaluate {
        val android = extensions.findByName("android")
        if (android is com.android.build.gradle.LibraryExtension) {
            val current = android.compileSdkVersion?.removePrefix("android-")?.toIntOrNull()
            if (current != null && current < 34) {
                android.compileSdkVersion(36)
            }
        }
    }
}
subprojects {
    project.evaluationDependsOn(":app")
}

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}
