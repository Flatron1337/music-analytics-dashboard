import 'dart:typed_data';

import 'story_saver_stub.dart'
    if (dart.library.html) 'story_saver_web.dart'
    if (dart.library.io) 'story_saver_io.dart';

Future<String?> saveStoryImage(Uint8List bytes, String filename) {
  return saveStoryImagePlatform(bytes, filename);
}
