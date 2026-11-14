# Actions from inventory variables

<!-- cspell:ignore selectattr thinpool -->

[![molecule](https://github.com/raven428/ansible-mega-var/actions/workflows/repo-test.yaml/badge.svg)](https://github.com/raven428/ansible-mega-var/actions/workflows/repo-test.yaml)

The role performs actions from inventory variables without creating a lot of tasks and copy-pasted roles

## Role release to Ansible galaxy

- clone me:

  ```bash
  git clone --recursive \
  git@github.com:raven428/ansible-mega-var.git \
  ansible-mega-var
  ```

- make tag and send to release:

  ```bash
  git checkout master && git pull
  git tag -fm $(git branch --sho) 1.0.10 && git push --force origin $(git describe)
  ```

## Example `site.yaml` (TLDR)

### For the whole role

In case you have most of the variables filled it's

```yaml
- name: Perform some files, dirs, and templates upload
  hosts: mega_var
  become: true
  handlers:
    - import_tasks: handlers/main.yaml
  roles:
    - role: mega-var
      vars:
        meva_packages: "{{ meva_site_packages }}"
        meva_groups2create: "{{ meva_site_groups2create }}"
        meva_users2create: "{{ meva_site_users2create }}"
        meva_getent: "{{ meva_site_getent }}"
        meva_dirs2create: "{{ meva_site_dirs2create }}"
        meva_templates2upload: "{{ meva_site_templates2upload }}"
        meva_files2upload: "{{ meva_site_files2upload }}"
        meva_content2upload: "{{ meva_site_content2upload }}"
        meva_tree2rsync: "{{ meva_site_tree2rsync }}"
        meva_systemd4units: "{{ meva_site_systemd4units }}"
        meva_key2user: "{{ meva_site_key2user }}"
        meva_file2down: "{{ meva_site_file2down }}"
        meva_partitions: "{{ meva_site_partitions }}"
        meva_lvg: "{{ meva_site_lvg }}"
        meva_lvol: "{{ meva_site_lvol }}"
        meva_filesystems: "{{ meva_site_filesystems }}"
        meva_mounts: "{{ meva_site_mounts }}"
        meva_ghr2down: "{{ meva_site_ghr2down }}"
        meva_file2down: "{{ meva_site_file2down }}"
  tags: [mega-var]
```

### By separate calls

In case you haven't filled most of the variables, a call of the role can be significantly speed up. Simple by using `tasks_from:` directive:

```yaml
- name: Separate mega-var calls examples
  hosts: mega_var
  become: true
  handlers:
    - import_tasks: handlers/main.yaml
  tasks:
    - name: Install some packages outside of the whole role call
      ansible.builtin.include_role:
        role: mega-var
        tasks_from: _apt.yaml
      loop_control:
        loop_var: i
      loop: "{{ meva_site_packages }}"
    - name: Ensure some groups outside of the whole role call
      ansible.builtin.include_role:
        role: mega-var
        tasks_from: _group.yaml
      loop_control:
        loop_var: i
      loop: "{{ meva_site_groups2create }}"
    - name: Ensure some users outside of the whole role call
      ansible.builtin.include_role:
        role: mega-var
        tasks_from: _user.yaml
      loop_control:
        loop_var: i
      loop: "{{ meva_site_users2create }}"
    - name: Ensure some dirs outside of the whole role call
      ansible.builtin.include_role:
        role: mega-var
        tasks_from: _file.yaml
      loop_control:
        loop_var: i
      loop: "{{ meva_site_dirs2create }}"
    - name: Ensure some templates outside of the whole role call
      ansible.builtin.include_role:
        role: mega-var
        tasks_from: _template.yaml
      loop_control:
        loop_var: i
      loop: "{{ meva_site_templates2upload }}"
    - name: Ensure some files outside of the whole role call
      ansible.builtin.include_role:
        role: mega-var
        tasks_from: _copy.yaml
      loop_control:
        loop_var: i
      loop: "{{ meva_site_files2upload }}"
- name: Download some files from GitHub releases example
  hosts: download_github
  become: true
  handlers:
    - import_tasks: handlers/main.yaml
  tasks:
    - name: Download some files from GitHub releases
      ansible.builtin.include_role:
        role: mega-var
        tasks_from: _download.yaml
      loop_control:
        loop_var: i
      loop: "{{ meva_site_ghr2down }}"
```

## Role variables description

All the variables except `meva_ghr2down` and `meva_file2down` is just wrapper and refers to according Ansible module documentation. Most keys of `meva_ghr2down` and `meva_file2down` variables also refers to `ansible.builtin.get_url` documentation

Here will be only non-obvious options of usage

### Common options of wrapper items

Every item of the wrapper variables, except `meva_file2down` and `meva_ghr2down`, accepts the following keys besides the module options:

- `no_log: true` hides the label, the result, and the diff of this item only, e.g., for a private key in `content` of `meva_files2upload`; for `meva_key2user` and `meva_systemd4units` the label of the `included:` line becomes `(censored due to no_log)`
- `loop_label` replaces the item printed in the `(item=…)` label, the whole item is printed by default
- `when`, `failed_when`, `changed_when` and `until` (the latter is ignored by `meva_packages`, which always retries until success) take an Ansible expression string without `{{ }}`, e.g., `changed_when: _task_result.rc == 2`, or a boolean; the expression is evaluated as is, nothing like `| default(…)` is appended to it, so a variable undefined in the expression is an error, use `x is defined and …` or `x | default(…)` explicitly: it fails the item, except `when` on ansible-core older than 2.21, where the error is ignored; when the key is absent the wrapper default applies, e.g., `_task_result.failed` for `failed_when`
- `meva_key` names the item: it replaces the entities in the task name, even with `no_log: true`, and becomes `meva_key` of the item record, see below; set it as a string: a non-string value, e.g., a number, becomes a string in the record on ansible-core 2.13 and 2.17 but keeps its type on 2.21, so a comparison in `selectattr` gives different results
- `meva_store: false` skips the record of this item, see below
- `meva_reset_here: true` makes the item a reset of the result list, see below

### Getent queries with `meva_getent` variable

Items of `meva_getent` are options of `ansible.builtin.getent`: `database` is mandatory, `key`, `service`, `split` and `fail_key` are optional; the common options above apply too. The whole role queries getent after groups and users and before files and directories. The module sets `getent_<database>` facts as usual, every call overwrites them

### Results of wrapper items

The results aren't saved by default. With `meva_results: true` every wrapper appends one record per item, in the order of execution, to its list `meva_<x>_results`, where `<x>` is the wrapper file name without `_` and `.yaml`: `meva_apt_results`, `meva_group_results`, `meva_user_results`, `meva_getent_results`, `meva_file_results`, `meva_template_results`, `meva_copy_results`, `meva_rsync_results`, `meva_systemd_results`, `meva_key_results`, `meva_parted_results`, `meva_lvg_results`, `meva_lvol_results`, `meva_filesystem_results`, `meva_mount_results`, `meva_command_results` and `meva_shell_results`. Downloads have no result list. With `meva_results: false` nothing is saved or reset: lists of previous calls with `meva_results: true` in the same run stay as they were, other lists are undefined; the wrappers neither run nor show the saving of records and the reset of the list before the call, only an explicit `meva_reset_here` item still checks its keys and shows its reset as skipped

- a record is the registered result of the module as is, e.g., `gid` in `meva_group_results` for a new and an existing group, `uid` in `meva_user_results`, except a new group or user in check mode, where the module returns neither, plus two keys:
  - `meva_status` – `ok`, `changed`, `skipped` or `failed`
  - `meva_key` – `meva_key` of the item or, without it, the natural key of the item: package names from `name`, `package` or `pkg` joined by `,` or `deb` for `meva_packages`, `name` for `meva_groups2create`, `name` or `user` for `meva_users2create`, `path`, `dest` or `name` for `meva_dirs2create`, `dest` for `meva_templates2upload`, `meva_files2upload` and `meva_tree2rsync`, `name` for `meva_systemd4units`, `user` for `meva_key2user`, `<device>:<number>` or `<device>` without `number` for `meva_partitions`, `vg` for `meva_lvg`, `<vg>/<lv>` (`lv` or `thinpool`) for `meva_lvol`, `dev` or `device` for `meva_filesystems`, `path` or `name` for `meva_mounts`, `cmd`, `argv` joined by a space or `free_form` for `meva_cmd2run`, `cmd` or `free_form` for `meva_run4shell`, `<database>:<key>` or `<database>` without `key` for `meva_getent`; an absent part is `undefined`
- a record of `meva_getent_results` holds only `database`, `key` (`null` without it), `results`, `meva_key` and `meva_status`, where `results` is `getent_<database>` from `ansible_facts` of the module result in the `{name: [fields]}` form or `null` when the result has no such facts, e.g., for a skipped query or a failure of the module; a query, which succeeded but is failed by `failed_when`, keeps its data. The module keys the data by the first field of the entry, not by the requested key: `key: "992"` of `database: group` gives `results.kvm`; the fields are strings; an absent key with `fail_key: false` gives `null` for this key: `results` is `{<key>: null}`; a name that occurs in the database several times gives a list of lists of fields instead of a list of fields, e.g., `database: services` without `key` gives two entries under `domain`, `53/tcp` and `53/udp`, so the form of the value depends on the data of the database
- a record is saved by a task right after the module task, so items skipped by `when` and failed with `ignore_errors: true` are saved too, while an item, which failed without `ignore_errors`, isn't saved: it stops the host as before, and an outer `rescue` gets its result as `ansible_failed_result`
- the saving task inherits `tags` of the item, so an item skipped by `--tags` or `--skip-tags` isn't saved
- records with the same `meva_key` aren't replaced: the history and the order are kept
- an item with `no_log: true` saves only `meva_key` and `meva_status`, without the module result; without `meva_key` of the item its record has `meva_key: (censored due to no_log)`, because the natural key, e.g., `cmd`, may contain a secret
- `meva_store: false` of an item skips its record
- `meva_reset: true` (default) empties the list of the wrapper before each call, `meva_reset: false` keeps the records of previous calls
- an item `- meva_reset_here: true` empties the list in the middle of the items; it allows only `when`, `tags` and `loop_label`, any other key fails the item even with `meva_results: false`; it doesn't depend on `meva_reset` and isn't saved itself
- the lists are `set_fact` facts: they live till the end of the `ansible-playbook` run and are shared by all calls of the role in it, including calls from other roles

Pick the last successful record of a key with filters only, `| list` before `last` is mandatory, because `selectattr` returns a generator and `last` calls `reversed()`:

```yaml
kvm_gid: "{{ (meva_group_results | selectattr('meva_key', 'eq', 'kvm')
  | selectattr('meva_status', 'in', ['ok', 'changed']) | list | last).gid }}"
```

### Simple HTTP download with `meva_file2down` variable

There are [the molecule tests](molecule/downloads/group_vars/all.yaml) cases description. Most options are available from `ansible.builtin.get_url`, `ansible.builtin.file` and `ansible.builtin.copy`

#### Single raw download (remote and local)

##### Case `1.1.1`

```yaml
- url: "http://url.to/download.ext"
  dest: "/dir/on/target/host/with/filename.ext"
  delegate_to: localhost
```

##### Case `1.1.2`

With `delegate_to: localhost` is set, file from `url` will be downloaded to Ansible controller first. Then `ansible.builtin.copy` will spread file to destination hosts. This can be useful when `url` source isn't able to handle a lot of requests from hosts in configuration

#### Single compressed download

##### Case `1.2.1`

```yaml
- url: "http://url.to/download.ext.gz"
  dest: "/dir/on/target/host/with/"
  creates: "filename.ext"
  archive: true
```

This option will decompress downloaded file. Parameter `dest` should contain the destination directory name only, without a filename.

Filename part of the decompressed file should be in `creates` key. The `archive: true` indicates that downloaded file should be decompressed extension from `uri`. Extension `gz`, `bz2`, `lz4`, `zst`, `lzma`, `xz` supported by [decompress](library/decompress.py) module. It can recognize file format only by extension, no content scan will be performed

Sometimes `uri` couldn't contain extension or even reliable filename. In this case you may set it by hand in `down_name` key. Temporary download will be placed to file in temporary directory with this name. Thus, decompress module able to handle file by extension

##### Case `1.2.2`

If `delegate_to: localhost` is set, then downloading will be performed on the Ansible controller, decompressed, then propagated to a remote host after decompress

#### Archive with a directory tree: complete unarchive

##### Case `1.3.1`

```yaml
- url: "http://url.to/download.tar.gz"
  creates: "filename.ext"
  dest: "/dir/on/target/host"
  archive: true
  delegate_to: localhost
  files: []
```

This will download a file to a host, perform `ansible.builtin.unarchive` and then traverse result directory with [chmod_tree](library/chmod_tree.py) module: directories to `dir_mode`, files with executive bit to `exec_mode` and non-executive files to `file_mode`

##### Case `1.3.2`

If `delegate_to: localhost` is set, then downloading will be performed on the Ansible controller then downloaded result will be propagated to the remote host before unarchive

#### Archive with a directory tree: pick-me something

##### Case `1.4.1`

```yaml
- url: "http://url.to/download.tar.gz"
  creates: "filename.ext"
  dest: "/dir/on/target/host"
  archive: true
  files:
    - name: "relative/dir/of/file-in-archive.ext"
      dest: "sub-dir/from/parent/dest"
    - name: "some/other/in-archive.dump"
      dest: "/dir/for/other/"
    - name: "one/more/file-in-archive.jpg"
      dest: "/one/more/dir/picture.jpg"
```

This will download the file to a target host, perform `ansible.builtin.unarchive`, then pick elements from list of `files:` and propagate it to certain path

##### Case `1.4.2`

If `delegate_to: localhost` is set, then downloading will be performed on the Ansible controller, perform `ansible.builtin.unarchive` also there, then pick elements from list of `files:` and propagate it to certain path

There are a lot of options in `files:` definitions (shown as `f.` below) the full list:

- Both `dest` and `f.dest` are either relative or undefined or empty will raise error
- If `dest` is defined, it should be absolute otherwise error will be raised. Other options are similar as above:
  - (`0.0.0`) Here `f.dest` can be empty or undefined, so `result = i.dest ~ '/' ~ f.name | basename`
  - (`0.0.1`) If `f.dest` ended by `/`, `result = i.dest ~ '/' ~ f.dest ~ '/' ~ f.name | basename`
  - (`0.0.2`) If `f.dest` is not ended by `/` then treated as file name: `result = i.dest ~ '/' ~ f.dest`
- Either `dest` is empty or `f.dest` starts with `/` the result defined by `f.dest` and `f.name` only:
  - (`0.1.0`) If `f.dest` finished by `/`, `result = f.dest ~ '/' ~ f.name | basename`
  - (`0.1.1`) If `f.dest` is not finished by `/` then treated as path with filename: `result = f.dest`

Parameter `f.name` can be directory then will be propagated recursively. In this case two options of `f.name` are available to upload: w/ and w/o trailing `/`. Other rules are same as above multiplied on these options:

- (`0.2.0`) If `f.name` ended by `/` only content of directory will be uploaded to the result
- (`0.2.1`) Else the whole directory with content will be uploaded

This is the `ansible.builtin.copy` behavior. In both cases destination directory will be automatically created despite the result ended with `/` or not

## Role development road-map

### Add `rsync` ability to some cases of pick-me

For cases `1.4.1` and `1.4.2` when source is a directory and destination already contain some other files it will not be deleted. Just the new files will be placed near with existing ones. It will be nice to support sync state of source and destination directories

It can be achieved by using `ansible.posix.synchronize` module in `_down2unp.yaml` with the `when` condition near `ansible.builtin.copy`. The latter also should obtain `when` for avoiding simultaneous usage of both transfer modules

### Add action plugin to decompress module

Unarchive module perform the upload of file to targets before unarchive, but decompress is not. This is inaccurate behavior, because upload of decompressed files may consume more traffic data than compressed. Also, this will consume more time to operate and this can be avoided

So, the better way is put compressed file to targets before decompress. This requires action plugin like done in unarchive. However, simple adding action plugin is not enough due to other role YAML-code expects decompressed file on the controller. So, these code also should be adapted

### Replace `docker` to `podman` driver in molecule

Failed yet. I'm not able to start `systemd` inside a `podman in podman` container according to [article](https://www.redhat.com/en/blog/podman-inside-container). Grok and ChatGPT help also didn't work. However, `docker in podman` is tolerable here

Docker in docker also works. I choose the podman as first layer for the rootless approach which is impossible with the docker as a first layer. Probably, `podman --remote` with `--url` to host socket in podman should work. But there are no support for this in `molecule_podman` driver
