import 'dart:io';
import 'dart:typed_data';

Future<String?> saveStoryImagePlatform(Uint8List bytes, String filename) async {
  try {
    Directory? dir;
    if (Platform.isAndroid) {
      dir = Directory('/storage/emulated/0/Download');
      if (!await dir.exists()) {
        dir = Directory.systemTemp;
      }
    } else {
      dir = Directory.systemTemp;
    }
    final file = File('${dir.path}/$filename');
    await file.writeAsBytes(bytes);
    return file.path;
  } catch (e) {
    return null;
  }
}
