/// What the QR code from `make start` holds: kanakku://connect?url=...&token=...
class ConnectLink {
  final String url, token;
  const ConnectLink(this.url, this.token);

  /// Null for anything that is not a Kanakku code.
  static ConnectLink? parse(String? raw) {
    final uri = Uri.tryParse(raw ?? '');
    if (uri == null || uri.scheme != 'kanakku' || uri.host != 'connect') return null;
    final url = uri.queryParameters['url'] ?? '';
    final token = uri.queryParameters['token'] ?? '';
    if (!url.startsWith('http') || token.isEmpty) return null;
    return ConnectLink(url, token);
  }
}
