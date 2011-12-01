Name: mod_nss
Version: 1.0.8
Release: 8%{?dist}
Summary: SSL/TLS module for the Apache HTTP server
Group: System Environment/Daemons
License: ASL 2.0
URL: http://directory.fedoraproject.org/wiki/Mod_nss
Source: http://directory.fedoraproject.org/sources/%{name}-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildRequires: nspr-devel, nss-devel >= 3.12.6
BuildRequires: httpd-devel, apr-devel, apr-util-devel
BuildRequires: pkgconfig
Requires(pre): httpd
Requires: %{_libdir}/libnssckbi.so
Requires: nss >= 3.12.6
Requires: nss-tools
# Change configuration to not conflict with mod_ssl
Patch1: mod_nss-conf.patch
# Generate a password-less NSS database
Patch2: mod_nss-gencert.patch
# Properly set blocking status when no data is available
Patch3: mod_nss-wouldblock.patch
# Add options for new negotation API
Patch4: mod_nss-negotiate.patch
Patch5: mod_nss-reverseproxy.patch

%description
The mod_nss module provides strong cryptography for the Apache Web
server via the Secure Sockets Layer (SSL) and Transport Layer
Security (TLS) protocols using the Network Security Services (NSS)
security library.

%prep
%setup -q
%patch1 -p1 -b .conf
%patch2 -p1 -b .gencert
%patch3 -p1 -b .wouldblock
%patch4 -p1 -b .negotiate
%patch5 -p1 -b .reverseproxy

# Touch expression parser sources to prevent regenerating it
touch nss_expr_*.[chyl]

%build

CFLAGS="$RPM_OPT_FLAGS"
export CFLAGS

NSPR_INCLUDE_DIR=`/usr/bin/pkg-config --variable=includedir nspr`
NSPR_LIB_DIR=`/usr/bin/pkg-config --variable=libdir nspr`

NSS_INCLUDE_DIR=`/usr/bin/pkg-config --variable=includedir nss`
NSS_LIB_DIR=`/usr/bin/pkg-config --variable=libdir nss`

%configure \
    --with-nss-lib=$NSS_LIB_DIR \
    --with-nss-inc=$NSS_INCLUDE_DIR \
    --with-nspr-lib=$NSPR_LIB_DIR \
    --with-nspr-inc=$NSPR_INCLUDE_DIR \
    --with-apr-config

make %{?_smp_mflags} all

%install
# The install target of the Makefile isn't used because that uses apxs
# which tries to enable the module in the build host httpd instead of in
# the build root.
rm -rf $RPM_BUILD_ROOT

mkdir -p $RPM_BUILD_ROOT%{_sysconfdir}/httpd/conf
mkdir -p $RPM_BUILD_ROOT%{_sysconfdir}/httpd/conf.d
mkdir -p $RPM_BUILD_ROOT%{_libdir}/httpd/modules
mkdir -p $RPM_BUILD_ROOT%{_sbindir}
mkdir -p $RPM_BUILD_ROOT%{_sysconfdir}/httpd/alias

install -m 644 nss.conf $RPM_BUILD_ROOT%{_sysconfdir}/httpd/conf.d/
install -m 755 .libs/libmodnss.so $RPM_BUILD_ROOT%{_libdir}/httpd/modules/
install -m 755 nss_pcache $RPM_BUILD_ROOT%{_sbindir}/
install -m 755 gencert $RPM_BUILD_ROOT%{_sbindir}/
ln -s ../../../%{_libdir}/libnssckbi.so $RPM_BUILD_ROOT%{_sysconfdir}/httpd/alias/
touch $RPM_BUILD_ROOT%{_sysconfdir}/httpd/alias/secmod.db
touch $RPM_BUILD_ROOT%{_sysconfdir}/httpd/alias/cert8.db
touch $RPM_BUILD_ROOT%{_sysconfdir}/httpd/alias/key3.db
touch $RPM_BUILD_ROOT%{_sysconfdir}/httpd/alias/install.log

%clean
rm -rf $RPM_BUILD_ROOT

%post
umask 077

if [ "$1" -eq 1 ] ; then
    if [ ! -e %{_sysconfdir}/httpd/alias/key3.db ]; then
        %{_sbindir}/gencert %{_sysconfdir}/httpd/alias > %{_sysconfdir}/httpd/alias/install.log 2>&1
    fi

    # Make sure that the database ownership is setup properly.
    /bin/find %{_sysconfdir}/httpd/alias -user root -name "*.db" -exec /bin/chgrp apache {} \;
    /bin/find %{_sysconfdir}/httpd/alias -user root -name "*.db" -exec /bin/chmod g+r {} \;
fi

%files
%defattr(-,root,root,-)
%doc README LICENSE docs/mod_nss.html
%config(noreplace) %{_sysconfdir}/httpd/conf.d/nss.conf
%{_libdir}/httpd/modules/libmodnss.so
%dir %{_sysconfdir}/httpd/alias/
%ghost %attr(0640,root,apache) %config(noreplace) %{_sysconfdir}/httpd/alias/secmod.db
%ghost %attr(0640,root,apache) %config(noreplace) %{_sysconfdir}/httpd/alias/cert8.db
%ghost %attr(0640,root,apache) %config(noreplace) %{_sysconfdir}/httpd/alias/key3.db
%ghost %config(noreplace) %{_sysconfdir}/httpd/alias/install.log
%{_sysconfdir}/httpd/alias/libnssckbi.so
%{_sbindir}/nss_pcache
%{_sbindir}/gencert

%changelog
* Mon Jun 14 2010 Rob Crittenden <rcritten@redhat.com> - 1.0.8-8
- Add Requires on nss-tools for default db creation (#603172)

* Thu May 20 2010 Rob Crittenden <rcritten@redhat.com> - 1.0.8-7
- Use remote hostname set by mod_proxy to compare to CN in peer cert (#591901)

* Thu Mar 18 2010 Rob Crittenden <rcritten@redhat.com> - 1.0.8-6
- Patch to add configuration options for new NSS negotiation API (#574187)
- Set minimum version of nss to 3.12.6 to pick up renegotiation fix

* Wed Feb 24 2010 Rob Crittenden <rcritten@redhat.com> - 1.0.8-5
- Add (pre) for Requires on httpd so we can be sure the user and group are
  already available
- Add file Requires on libnssckbi.so so symlink can't fail
- Use _sysconfdir macro instead of /etc

* Tue Feb 23 2010 Rob Crittenden <rcritten@redhat.com> - 1.0.8-4
- Remove unused variable and perl substitution for gencert. gencert used to
  have separate variables for NSS & NSPR libraries, that is gone now so this
  variable and substitution aren't needed.
- Added comments to patch to identify what they do

* Wed Jan 27 2010 Rob Crittenden <rcritten@redhat.com> - 1.0.8-3
- The location of libnssckbi.so moved from /lib[64] to /usr/lib[64] (#558545)
- Don't generate output when the default NSS database is generated (#538859)

* Mon Nov 30 2009 Dennis Gregorovic <dgregor@redhat.com> - 1.0.8-2.1
- Rebuilt for RHEL 6

* Sat Jul 25 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.0.8-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Mon Mar  2 2009 Rob Crittenden <rcritten@redhat.com> - 1.0.8-1
- Update to 1.0.8
- Add patch that fixes NSPR layer bug

* Wed Feb 25 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.0.7-11
- Rebuilt for https://fedoraproject.org/wiki/Fedora_11_Mass_Rebuild

* Mon Aug 11 2008 Tom "spot" Callaway <tcallawa@redhat.com> - 1.0.7-10
- fix license tag

* Mon Jul 28 2008 Rob Crittenden <rcritten@redhat.com> - 1.0.7-9
- rebuild to bump NVR

* Mon Jul 14 2008 Rob Crittenden <rcritten@redhat.com> - 1.0.7-8
- Don't force module de-init during the configuration stage (453508)

* Thu Jul 10 2008 Rob Crittenden <rcritten@redhat.com> - 1.0.7-7
- Don't inherit the MP cache in multi-threaded mode (454701)
- Don't initialize NSS in each child if SSL isn't configured

* Wed Jul  2 2008 Rob Crittenden <rcritten@redhat.com> - 1.0.7-6
- Update the patch for FIPS to include fixes for nss_pcache, enforce
  the security policy and properly initialize the FIPS token.

* Mon Jun 30 2008 Rob Crittenden <rcritten@redhat.com> - 1.0.7-5
- Include patch to fix NSSFIPS (446851)

* Mon Apr 28 2008 Rob Crittenden <rcritten@redhat.com> - 1.0.7-4
- Apply patch so that mod_nss calls NSS_Init() after Apache forks a child
  and not before. This is in response to a change in the NSS softtokn code
  and should have always been done this way. (444348)
- The location of libnssckbi moved from /usr/lib[64] to /lib[64]
- The NSS database needs to be readable by apache since we need to use it
  after the root priviledges are dropped.

* Tue Feb 19 2008 Fedora Release Engineering <rel-eng@fedoraproject.org> - 1.0.7-3
- Autorebuild for GCC 4.3

* Thu Oct 18 2007 Rob Crittenden <rcritten@redhat.com> 1.0.7-2
- Register functions needed by mod_proxy if mod_ssl is not loaded.

* Fri Jun  1 2007 Rob Crittenden <rcritten@redhat.com> 1.0.7-1
- Update to 1.0.7
- Remove Requires for nss and nspr since those are handled automatically
  by versioned libraries
- Updated URL and Source to reference directory.fedoraproject.org

* Mon Apr  9 2007 Rob Crittenden <rcritten@redhat.com> 1.0.6-2
- Patch to properly detect the Apache model and set up NSS appropriately
- Patch to punt if a bad password is encountered
- Patch to fix crash when password.conf is malformatted
- Don't enable ECC support as NSS doesn't have it enabled (3.11.4-0.7)

* Mon Oct 23 2006 Rob Crittenden <rcritten@redhat.com> 1.0.6-1
- Update to 1.0.6

* Fri Aug 04 2006 Rob Crittenden <rcritten@redhat.com> 1.0.3-4
- Include LogLevel warn in nss.conf and use separate log files

* Fri Aug 04 2006 Rob Crittenden <rcritten@redhat.com> 1.0.3-3
- Need to initialize ECC certificate and key variables

* Fri Aug 04 2006 Jarod Wilson <jwilson@redhat.com> 1.0.3-2
- Use %%ghost for db files and install.log

* Tue Jun 20 2006 Rob Crittenden <rcritten@redhat.com> 1.0.3-1
- Initial build
