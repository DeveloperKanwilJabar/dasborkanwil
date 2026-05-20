const browsersync = require('browser-sync').create();
const cached = require('gulp-cached');
const del = require('del');
const fileinclude = require('gulp-file-include');
const gulp = require('gulp');
const gulpif = require('gulp-if');
const npmdist = require('gulp-npm-dist');
const replace = require('gulp-replace');
const uglify = require('gulp-uglify');
const useref = require('gulp-useref-plus');
const rename = require('gulp-rename');
const sass = require('gulp-sass')(require('sass'));
const autoprefixer = require("gulp-autoprefixer");
const sourcemaps = require("gulp-sourcemaps");
const cleanCSS = require('gulp-clean-css');
const rtlcss = require('gulp-rtlcss');
const fs = require('fs');
const { exec } = require('child_process'); // Tambahan untuk eksekusi perintah shell

const isSourceMap = true;
const sourceMapWrite = (isSourceMap) ? "./" : false;

const paths = {
    base: {
        base: { dir: './' },
        node: { dir: './node_modules' }
    },
    dist: {
        base: {
            dir: './app/static',
            assets: './app/static/'
        },
        libs: { dir: './app/static/libs' },
        css: { dir: './app/static/css' },
        js: {
            dir: './app/static/js',
            files: './app/static/js/pages'
        },
    },
    src: {
        base: {
            dir: './app/src',
            assets: './app/src/**/*'
        },
        js: {
            dir: './app/src/js',
            pages: './app/src/js/pages',
            files: './app/src/js/pages/*.js',
            main: './app/src/js/*.js'
        },
        scss: {
            dir: './app/src/scss',
            files: './app/src/scss/**/*',
            main: './app/src/scss/config/app.scss'
        },
        icon: {
            dir: './app/src/scss',
            files: './app/src/scss/icons.scss',
            main: './app/src/scss/*.scss'
        },
        bootstrap: {
            files: './app/src/scss/config/bootstrap.scss',
            typeFiles: './app/src/scss/config/bootstrap.scss',
            components: './app/src/scss/components/*',
            light: './app/src/scss/config/_theme*',
            variables: './app/src/scss/config/_variables*'
        },
        custom: {
            dir: './app/src/scss/config/custom.scss',
            files: './app/src/scss/config/custom.scss',
            main: './app/src/scss/config/custom.scss'
        },
    }
};

// --- Task untuk Copy Gambar & Font secara Manual (Shell Command) ---
// Cara ini menghindari kerusakan file biner (corrupt) oleh stream Gulp
gulp.task('copy:assets:manual', function (cb) {
    // Memastikan folder static ada, lalu copy folder images dan fonts
    // -a menjaga permission, -r untuk recursive
    exec('mkdir -p ./app/static/images ./app/static/fonts && cp -ar ./app/src/images/. ./app/static/images/ && cp -ar ./app/src/fonts/. ./app/static/fonts/', function (err, stdout, stderr) {
        if (err) {
            console.error(`Error copy manual: ${stderr}`);
        }
        cb(err);
    });
});

gulp.task('browsersync', function (callback) {
    var baseDir = paths.dist.base.dir;
    browsersync.init({
        server: {
            baseDir: [baseDir, paths.src.base.dir, paths.base.base.dir]
        }
    });
    callback();
});

gulp.task('browsersyncReload', function (callback) {
    browsersync.reload();
    callback();
});

gulp.task('watch', async function () {
    gulp.watch([paths.src.scss.files, '!' + paths.src.custom.files, '!' + paths.src.icon.files, '!' + paths.src.bootstrap.typeFiles, '!' + paths.src.bootstrap.light, '!' + paths.src.bootstrap.variables], gulp.series('scss'));
    gulp.watch([paths.src.bootstrap.typeFiles, '!' + paths.src.bootstrap.components, '!' + paths.src.bootstrap.light], gulp.series('bootstrap'));
    gulp.watch([paths.src.bootstrap.light, paths.src.bootstrap.variables], gulp.series('bootstrap', 'scss'));
    gulp.watch(paths.src.icon.files, gulp.series('icon'));
    gulp.watch(paths.src.custom.files, gulp.series('custom'));
    gulp.watch([paths.src.js.dir], gulp.series('js'));
    gulp.watch([paths.src.js.pages], gulp.series('jsPages'));
    // Watch juga folder images/fonts jika ada perubahan
    gulp.watch(['./app/src/images/**/*', './app/src/fonts/**/*'], gulp.series('copy:assets:manual'));
});

gulp.task('js', async function () {
    var destPath = paths.dist.js.dir;
    return gulp.src(paths.src.js.main).pipe(uglify()).pipe(gulp.dest(destPath));
});

gulp.task('jsPages', function () {
    var JsPagePath = paths.dist.js.files;
    return gulp.src(paths.src.js.files).pipe(uglify()).pipe(gulp.dest(JsPagePath));
});

gulp.task('bootstrap', function () {
    var scssFiles = paths.src.bootstrap.files;
    var cssDest = paths.dist.css.dir;
    gulp.src(scssFiles)
        .pipe(sourcemaps.init())
        .pipe(sass.sync().on('error', sass.logError))
        .pipe(autoprefixer())
        .pipe(gulp.dest(cssDest))
        .pipe(cleanCSS())
        .pipe(rename({ suffix: ".min" }))
        .pipe(sourcemaps.write(sourceMapWrite))
        .pipe(gulp.dest(cssDest));

    return gulp.src(scssFiles)
        .pipe(sourcemaps.init())
        .pipe(sass.sync().on('error', sass.logError))
        .pipe(autoprefixer())
        .pipe(rtlcss())
        .pipe(gulp.dest(cssDest))
        .pipe(cleanCSS())
        .pipe(rename({ suffix: "-rtl.min" }))
        .pipe(sourcemaps.write(sourceMapWrite))
        .pipe(gulp.dest(cssDest));
});

gulp.task('scss', function () {
    var scssFiles = paths.src.scss.main;
    var cssDest = paths.dist.css.dir;
    gulp.src(scssFiles)
        .pipe(sourcemaps.init())
        .pipe(sass.sync().on('error', sass.logError))
        .pipe(autoprefixer())
        .pipe(gulp.dest(cssDest))
        .pipe(cleanCSS())
        .pipe(rename({ suffix: ".min" }))
        .pipe(sourcemaps.write(sourceMapWrite))
        .pipe(gulp.dest(cssDest));

    return gulp.src(scssFiles)
        .pipe(sourcemaps.init())
        .pipe(sass.sync().on('error', sass.logError))
        .pipe(autoprefixer())
        .pipe(rtlcss())
        .pipe(gulp.dest(cssDest))
        .pipe(cleanCSS())
        .pipe(rename({ suffix: "-rtl.min" }))
        .pipe(sourcemaps.write(sourceMapWrite))
        .pipe(gulp.dest(cssDest));
});

gulp.task('custom', async function () {
    var scssFiles = paths.src.custom.main;
    var cssDest = paths.dist.css.dir;
    gulp.src(scssFiles)
        .pipe(sourcemaps.init())
        .pipe(sass.sync().on('error', sass.logError))
        .pipe(autoprefixer())
        .pipe(gulp.dest(cssDest))
        .pipe(cleanCSS())
        .pipe(rename({ suffix: ".min" }))
        .pipe(sourcemaps.write(sourceMapWrite))
        .pipe(gulp.dest(cssDest));

    return gulp.src(scssFiles)
        .pipe(sourcemaps.init())
        .pipe(sass.sync().on('error', sass.logError))
        .pipe(autoprefixer())
        .pipe(rtlcss())
        .pipe(gulp.dest(cssDest))
        .pipe(cleanCSS())
        .pipe(rename({ suffix: "-rtl.min" }))
        .pipe(sourcemaps.write(sourceMapWrite))
        .pipe(gulp.dest(cssDest));
});

gulp.task('icon', async function () {
    var cssDest = paths.dist.css.dir;
    return gulp.src(paths.src.icon.main)
        .pipe(sass.sync().on('error', sass.logError))
        .pipe(autoprefixer())
        .pipe(gulp.dest(cssDest))
        .pipe(cleanCSS())
        .pipe(rename({ suffix: ".min" }))
        .pipe(gulp.dest(cssDest));
});

gulp.task('clean:dist', function (callback) {
    del.sync(paths.dist.base.dir);
    callback();
});

// Task ini sekarang hanya meng-copy file teks/non-biner sisanya
gulp.task('copy:all', function (cb) {
    var destPath = paths.dist.base.assets;
    return gulp.src([
            paths.src.base.assets,
            '!' + paths.src.scss.files,
            '!' + paths.src.js.main,
            '!' + paths.src.js.files,
            '!' + paths.src.scss.dir,
            '!' + './app/src/images/**/*', // Dikecualikan karena sudah dihandle manual
            '!' + './app/src/fonts/**/*'   // Dikecualikan karena sudah dihandle manual
        ])
        .pipe(gulp.dest(destPath));
});

gulp.task('copy:libs', function () {
    var destPath = paths.dist.libs.dir;
    return gulp.src(npmdist({ replaceDefaultExcludes: isSourceMap, excludes: ['/**/*.txt'] }), {
            base: paths.base.node.dir
        })
        .pipe(rename(function (path) {
            path.dirname = path.dirname.replace(/\/static/, '');
        }))
        .pipe(gulp.dest(destPath));
});

// --- PERBAIKAN ALUR BUILD ---
// 1. Bersihkan folder dist.
// 2. Jalankan copy manual (images/fonts) DAN copy lainnya secara paralel.
// 3. Terakhir, pastikan scss terkompilasi dengan benar.
gulp.task('build', gulp.series(
    'clean:dist',
    gulp.parallel('copy:assets:manual', 'copy:all', 'copy:libs', 'bootstrap', 'scss', 'js', 'jsPages', 'icon', 'custom'),
    'scss' // Menjamin scss dijalankan ulang jika ada dependensi yang tertinggal
));

gulp.task('default', gulp.series(
    'clean:dist',
    gulp.parallel('copy:assets:manual', 'copy:all', 'copy:libs', 'bootstrap', 'scss', 'js', 'jsPages', 'icon', 'custom'),
    'watch'
));
