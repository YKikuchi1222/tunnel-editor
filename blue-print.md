# blue-print.md
このファイルは、このリポジトリで開発するアプリの初期設計提案を示す。

# 何が欲しいか
現在、1台のssh先 (ws4, このPC) に、ローカルのPCからsshとtunnelで接続している。sshはCLI運用、tunnelはvscode運用のためである。terminal側から開きたいファイルが見つかっている時に、そのパスを検索してからvscode画面で探すのは手間がかかります。
そこで、terminal で`e [ファイル名]` をしたら、トンネルに接続しているvscodeにファイルが開かれるようにしたい。この`e`に相当するものを作れ。

# 想定する環境
## tunnel
- ローカルPCからsshし、tmux し、code tunnel で設置される。
- デタッチされ、長時間設置されたままになる。

## vscode 
- ローカルPCで起動し、tunnelに接続
- 時折接続が切れたり、再起動される。
- vscode上でterminalを開くことはあまりない。

## terminal (ssh-tmux)
- ローカルでterminal起動し、このPCにsshし、tmuxして運用している。
- 各種AIエージェントや時折vimなど起動して言える
- tunnel とは別のtmuxセッション

# 期待する挙動
- terminal (ssh-tmux)で`e [ファイル名]`したら、ファイルがvscode側に開かれる。
- vscode切断再接続してもユーザーは何の設定もいらない
- ファイル名は相対パス、フルパス、正規表現が考えられる。最低限正規表現以外で指定した時に開けることを求める。
- ユーザーが何の手動設定もしなくて良いこと。

# パフォーマンス要件
- 日常的に大量に呼ぶ可能性があるため、体感上即時に動くこと。
- 常駐 daemon は原則不要。
- 1回の open request のために重い filesystem scan を毎回行わないこと。
- ただし、軽量な /proc 探索や runtime directory 探索は許容する。
- 必要なら短時間の cache を導入してもよいが、stale IPC を保持し続けないこと。