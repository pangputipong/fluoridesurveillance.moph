/* E-Fluoride Pro Frontend Application Logic */

$(document).ready(function() {
    // ----------------------------------------------------
    // 1. Dark Mode Toggle & Sidebar Control
    // ----------------------------------------------------
    if(localStorage.getItem('theme') === 'dark') {
        $('body').addClass('dark');
        $('#chkDarkMode').prop('checked', true);
    }

    $('#chkDarkMode').change(function() {
        if(this.checked) {
            $('body').addClass('dark');
            localStorage.setItem('theme', 'dark');
        } else {
            $('body').removeClass('dark');
            localStorage.setItem('theme', 'light');
        }
        setTimeout(() => { if (map) map.invalidateSize(); }, 350);
    });

    $('#sidebarToggle').click(function() {
        $('#sidebar').toggleClass('collapsed');
        if($(window).width() < 992) {
            $('#sidebar').toggleClass('show');
        }
        setTimeout(() => { if (map) map.invalidateSize(); }, 350);
    });

    // ----------------------------------------------------
    // 2. Authentication Logic
    // ----------------------------------------------------
    if(sessionStorage.getItem('adminToken')) {
        $('#btnLoginMenu').hide();
        $('#adminMenuSection').show();
        $('#btnLogoutMenu').show();
        $('#userProfileTop').css('display', 'flex');
        setTimeout(updateMenuVisibility, 500);
    }

    $('#btnSubmitLogin').click(function() {
        let username = $('#loginUsername').val() || 'admin';
        let pwd = $('#loginPassword').val();
        fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: username, password: pwd })
        })
        .then(res => res.json()).then(data => { 
            if(data.success) {
                sessionStorage.setItem('adminToken', data.token);
                sessionStorage.setItem('userRole', data.role);
                sessionStorage.setItem('userName', username);
                $('#loginModal').modal('hide');
                $('#loginPassword').val('');
                $('#btnLoginMenu').hide();
                $('#adminMenuSection').slideDown();
                $('#btnLogoutMenu').show();
                $('#userProfileTop').css('display', 'flex');
                updateMenuVisibility();
            } else {
                alert(data.message);
            } 
        }).catch(err => {
            alert('ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้');
        });
    });

    $('#btnLogoutMenu').click(function() {
        sessionStorage.removeItem('adminToken');
        $('#adminMenuSection').slideUp();
        $(this).hide();
        $('#btnLoginMenu').show();
        $('#userProfileTop').hide();
    });

    // ----------------------------------------------------
    // 3. Dynamic Drag & Drop File Upload
    // ----------------------------------------------------
    let dropArea = document.getElementById('dropzoneArea');
    let fileInput = document.getElementById('fileInputDummy');

    if (dropArea) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
        });
        function preventDefaults(e) { e.preventDefault(); e.stopPropagation(); }

        ['dragenter', 'dragover'].forEach(eventName => { dropArea.addEventListener(eventName, highlight, false); });
        ['dragleave', 'drop'].forEach(eventName => { dropArea.addEventListener(eventName, unhighlight, false); });
        function highlight(e) { dropArea.classList.add('dragover'); }
        function unhighlight(e) { dropArea.classList.remove('dragover'); }

        dropArea.addEventListener('drop', handleDrop, false);
        function handleDrop(e) {
            let dt = e.dataTransfer; let files = dt.files;
            if(files.length > 0) { triggerUpload(files[0]); }
        }
    }

    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            if(this.files.length > 0) { triggerUpload(this.files[0]); this.value = ''; }
        });
    }

    function triggerUpload(file) {
        let formData = new FormData(); 
        formData.append("file", file); 
        formData.append("category", $('#uploadCat').val());
        
        $('#uploadFormArea').hide(); 
        $('#importStatusScanning').show(); 
        
        fetch('/api/upload_data', {
            method: 'POST',
            headers: { 'Authorization': sessionStorage.getItem('adminToken') || '' },
            body: formData
        })
        .then(res => { if(res.status === 401) throw new Error('Unauthorized'); return res.json(); })
        .then(data => { 
            $('#importStatusScanning').hide(); 
            if(data.success) { 
                $('#resNew').text(data.summary.new);
                $('#resUpd').text(data.summary.updated);
                $('#resErr').text(data.summary.error);
                
                let tbody = '';
                data.details.forEach(r => {
                    let trClass = ''; let badge = '';
                    if(r.status === 'new') { trClass = 'status-new'; badge = '<span class="badge bg-success">ใหม่</span>'; }
                    else if(r.status === 'updated') { trClass = 'status-updated'; badge = '<span class="badge bg-warning text-dark">อัปเดต</span>'; }
                    else { trClass = 'status-error'; badge = '<span class="badge bg-danger">ผิดพลาด</span>'; }
                    tbody += `<tr class="${trClass}"><td>${r.index}</td><td>${r.reference}</td><td>${badge}</td><td>${r.remark}</td></tr>`;
                });
                $('#importResultBody').html(tbody);
                $('#importResultArea').fadeIn(); 
            } else { 
                alert('อัปโหลดล้มเหลว: ' + data.message); 
                $('#uploadFormArea').show();
            } 
        })
        .catch(err => { 
            $('#importStatusScanning').hide(); 
            $('#uploadFormArea').show();
            if(err.message === 'Unauthorized') alert('กรุณาเข้าสู่ระบบแอดมินก่อนอัปโหลดไฟล์!'); else alert('เกิดข้อผิดพลาดในการเชื่อมต่อ: ' + err.message); 
        });
    }

    // ----------------------------------------------------
    // 4. Schema Builder Control & Variable Mapping
    // ----------------------------------------------------
    $(document).on('change', '.db-col-sel', function() { 
        let row = $(this).closest('.table-builder-row');
        let input = row.find('.formula-input'); 
        let helperBtn = row.find('.btn-formula-helper');
        
        if($(this).val() === 'f') { 
            input.prop('disabled', false).attr('placeholder', 'เช่น: [screened_kids]/[total_kids]*100').focus(); 
            helperBtn.prop('disabled', false); 
        } else { 
            input.prop('disabled', true).val(''); 
            helperBtn.prop('disabled', true);  
        } 
    });

    $(document).on('click', '.insert-var-btn', function(e) {
        e.preventDefault();
        let valToInsert = $(this).data('val');
        let inputField = $(this).closest('.input-group').find('.formula-input');
        
        if(!inputField.prop('disabled')) {
            let currentVal = inputField.val();
            inputField.val(currentVal + valToInsert).focus();
        }
    });

    // PDF Exporting
    $(document).on('click', '.btnExportPDF', function() {
        logVisit(currentType, 'EXPORT');
        $('#pdfPreviewModal').modal('show');
        $('#pdfPreviewLoading').show();
        $('#pdfPreviewContainer').hide();
        
        // Hide elements that shouldn't be in the PDF preview
        $('.btn, .fly-to-btn, .map-layer-toggle, .leaflet-control-zoom, #btnToggleMapExpand').hide();
        
        let element = document.getElementById('pdfPrintArea');
        
        html2canvas(element, {
            scale: 2,
            useCORS: true,
            logging: false,
            allowTaint: true
        }).then(canvas => {
            // Restore hidden elements back on the page
            $('.btn, .fly-to-btn, .map-layer-toggle, .leaflet-control-zoom, #btnToggleMapExpand').show();
            
            let imgData = canvas.toDataURL('image/jpeg', 0.95);
            $('#pdfPreviewImage').attr('src', imgData);
            $('#pdfPreviewLoading').hide();
            $('#pdfPreviewContainer').show();
        }).catch(err => {
            $('.btn, .fly-to-btn, .map-layer-toggle, .leaflet-control-zoom, #btnToggleMapExpand').show();
            alert('ไม่สามารถประมวลผลตัวอย่าง PDF ได้: ' + err.message);
            $('#pdfPreviewModal').modal('hide');
        });
    });

    $('#btnConfirmDownloadPDF').click(function() {
        let originalBtn = $(this).html();
        $(this).html('<i class="fas fa-spinner fa-spin"></i> กำลังสร้างไฟล์...').prop('disabled', true);
        let element = document.getElementById('pdfPrintArea');
        let opt = {
            margin: [0.5, 0.2, 0.5, 0.2],
            filename: currentType + '_Report.pdf',
            image: { type: 'jpeg', quality: 0.98 },
            html2canvas: { scale: 2, useCORS: true, logging: false },
            jsPDF: { unit: 'in', format: 'a4', orientation: 'landscape' }
        };
        
        $('.btn, .fly-to-btn, .map-layer-toggle, .leaflet-control-zoom, #btnToggleMapExpand').hide(); 
        html2pdf().set(opt).from(element).save().then(() => { 
            $('.btn, .fly-to-btn, .map-layer-toggle, .leaflet-control-zoom, #btnToggleMapExpand').show(); 
            $('#pdfPreviewModal').modal('hide');
            $(this).html(originalBtn).prop('disabled', false);
        });
    });

    const dbFieldsList = ['hospcode', 'check_date', 'region', 'health_zone', 'province', 'district', 'subdistrict', 'hosp_name', 'total_kids', 'screened_kids', 'fluorosis_cases', 'pct_fluorosis', 'severe_cases', 'dean_index_status', 'location_name', 'water_type', 'fluoride_level', 'status', 'latitude', 'longitude', 'house_no', 'moo', 'remark', 'data_source'];
    let existingSchemas = {}; 
    const apiToDbRefMap = { 'hospcode': 'รหัสหน่วยบริการ', 'check_date': 'วันที่ตรวจ', 'region': 'ภาค', 'health_zone': 'เขตสุขภาพ', 'province': 'จังหวัด', 'district': 'อำเภอ', 'subdistrict': 'ตำบล', 'location_name': 'สถานที่', 'water_type': 'ประเภทแหล่งน้ำ', 'fluoride_level': 'ปริมาณฟลูออไรด์ (mg/L)', 'status': 'สถานการณ์', 'latitude': 'ละติจูด', 'longitude': 'ลองจิจูด', 'total_kids': 'จำนวนเด็กทั้งหมด', 'screened_kids': 'จำนวนตรวจ', 'fluorosis_cases': 'พบฟันตกกระ', 'pct_fluorosis': 'ร้อยละเด็กฟันตกกระ', 'severe_cases': 'severe_cases', 'hosp_name': 'ชื่อหน่วยบริการ', 'dean_index_status': 'สถานการณ์', 'house_no': 'บ้านเลขที่', 'moo': 'หมู่ที่', 'remark': 'หมายเหตุ', 'data_source': 'แหล่งข้อมูล' };

    function updateChartDropdowns() {
        let fields = []; $('#tableSchemaContainer .col-name').each(function() { let v = $(this).val().trim(); if(v) fields.push(v); });
        let buildOpts = (val) => { let h = '<option value="">-- ไม่ใช้ / ค่าเริ่มต้น --</option>'; fields.forEach(f => { h += `<option value="${f}" ${f===val?'selected':''}>${f}</option>`; }); return h; };
        
        $('#chartPropCol').html(buildOpts($('#chartPropCol').val()));
        $('#chartDrillCol').html(buildOpts($('#chartDrillCol').val()));
        $('#chartMapCol').html(buildOpts($('#chartMapCol').val()));
        for(let i=1; i<=4; i++) { $(`#kpi${i}_col`).html(buildOpts($(`#kpi${i}_col`).val())); }
    }
    $(document).on('input', '.col-name', updateChartDropdowns);

    function createGroupRuleRow(op='<', val1='', val2='', label='') {
        let showVal2 = (op === 'between') ? '' : 'display:none;';
        let html = `<div class="group-rule-row mb-2 p-2 bg-white border rounded"><div class="d-flex gap-1 mb-1"><select class="form-select form-select-sm rule-op" style="width: 75px;"><option value="<" ${op==='<'?'selected':''}>&lt;</option><option value="<=" ${op==='<='?'selected':''}>&lt;=</option><option value=">" ${op==='>'?'selected':''}>&gt;</option><option value=">=" ${op==='>='?'selected':''}>&gt;=</option><option value="between" ${op==='between'?'selected':''}>ช่วง</option><option value="==" ${op==='=='?'selected':''}>= (คำ)</option><option value="contains" ${op==='contains'?'selected':''}>มีคำว่า</option></select><input type="text" class="form-control form-control-sm rule-val1" placeholder="ค่า" value="${val1}"><input type="text" class="form-control form-control-sm rule-val2" placeholder="ถึงค่า" value="${val2}" style="${showVal2}"></div><div class="d-flex gap-1"><input type="text" class="form-control form-control-sm rule-label" placeholder="ชื่อกลุ่ม (เช่น ปกติ)" value="${label}"><button class="btn btn-sm btn-outline-danger btn-remove-rule"><i class="fas fa-times"></i></button></div></div>`;
        $('#groupRulesContainer').append(html);
    }

    $('#enableGrouping').change(function() { if(this.checked) $('#groupingBuilder').slideDown(); else $('#groupingBuilder').slideUp(); });
    $('#btnAddGroupRule').click(function() { createGroupRuleRow(); });
    $(document).on('change', '.rule-op', function() { if($(this).val() === 'between') $(this).closest('.group-rule-row').find('.rule-val2').show(); else $(this).closest('.group-rule-row').find('.rule-val2').hide(); });
    $(document).on('click', '.btn-remove-rule', function() { $(this).closest('.group-rule-row').remove(); });

    function fetchSchemas() {
        return fetch('/api/get_schemas').then(res => res.json()).then(data => {
            if(data.success) {
                existingSchemas = {};
                let envSetHtml = '<div class="small fw-bold text-muted px-2 mb-1 mt-2">หมวดสิ่งแวดล้อม</div>'; let healthSetHtml = '<div class="small fw-bold text-muted px-2 mb-1 mt-3">หมวดสุขภาพ</div>';
                let envMenuHtml = ''; let healthMenuHtml = ''; let tabsHtml = '<li class="nav-item"><a class="nav-link active menu-trigger" data-type="ทั้งหมด"><i class="fas fa-chart-pie"></i> หน้าหลัก (ภาพรวม)</a></li>';

                let preferredOrder = [
                    'คุณภาพแหล่งน้ำ', 
                    'คุณภาพน้ำประปา', 
                    'คุณภาพน้ำบาดาล', 
                    'โรงงานผลิตน้ำ', 
                    'สภาวะฟันตกกระ (เด็ก)'
                ];

                let reportNames = Object.keys(data.data);
                reportNames.sort((a, b) => {
                    let idxA = preferredOrder.indexOf(a);
                    let idxB = preferredOrder.indexOf(b);
                    if(idxA === -1) idxA = 999;
                    if(idxB === -1) idxB = 999;
                    return idxA - idxB;
                });

                for(let repName of reportNames) {
                    let cat = data.data[repName].category;
                    existingSchemas[repName] = { 
                        category: cat, 
                        fields: data.data[repName].fields.map(s => ({ name: s.name, type: s.type, db_ref: s.type === 'Formula' ? 'f' : s.db_ref, formula: s.formula || '' })),
                        config: data.data[repName].config || {proportion:'', proportion_rules:[], drilldown:'', map:'', kpis:[]}
                    };
                    let setItem = `<a href="#" class="list-group-item list-group-item-action text-muted" data-report="${repName}" data-category="${cat}">${repName}</a>`;
                    let menuItem = `<a class="submenu-link menu-trigger" data-type="${repName}" data-category="${cat}">${repName}</a>`;
                    let icon = cat === 'health' ? 'fa-tooth' : 'fa-leaf';
                    let tabItem = `<li class="nav-item"><a class="nav-link menu-trigger" data-type="${repName}" data-category="${cat}"><i class="fas ${icon}"></i> ${repName}</a></li>`;
                    
                    if(cat === 'summary') {
                        envSetHtml = `<div class="small fw-bold text-theme px-2 mb-1 mt-2">ตั้งค่าระบบส่วนกลาง</div>${setItem}` + envSetHtml;
                    } else if(cat === 'health') { 
                        healthSetHtml += setItem; healthMenuHtml += menuItem; tabsHtml += tabItem;
                    } else { 
                        envSetHtml += setItem; envMenuHtml += menuItem; tabsHtml += tabItem;
                    }
                }
                $('#reportListGroup').html(envSetHtml + healthSetHtml); $('#envSubmenu .submenu').html(envMenuHtml); $('#healthSubmenu .submenu').html(healthMenuHtml); $('#typeTabs').html(tabsHtml);
            }
        });
    }

    function createBuilderRow(name = '', dbVal = '', formula = '') {
        let dbOptionsHtml = dbFieldsList.map(col => `<option value="${col}" ${col === dbVal ? 'selected' : ''}>${col}</option>`).join(''); let isF = (dbVal === 'f');
        let varMenuHtml = dbFieldsList.map(col => `<li><a class="dropdown-item insert-var-btn" href="#" data-val="[${col}]" style="font-size: 0.85rem;"><i class="fas fa-plus-circle text-success me-2"></i>[${col}]</a></li>`).join('');

        $('#tableSchemaContainer').append(`
        <div class="table-builder-row row g-2 mb-2 p-2 align-items-center border rounded mx-0" style="background: #fff; border-color: var(--primary-color) !important;">
            <div class="col-3"><input type="text" class="form-control form-control-custom col-name" placeholder="ชื่อฟิลด์หน้าเว็บ" value="${name}"></div>
            <div class="col-4">
                <select class="form-select form-control-custom db-col-sel">
                    <option value="" ${dbVal === '' ? 'selected' : ''}>-- ไม่ใช้ DB --</option>
                    <option value="f" ${isF ? 'selected' : ''}>[ สูตรคำนวณ ]</option>
                    ${dbOptionsHtml}
                </select>
            </div>
            <div class="col-4">
                <div class="input-group">
                    <input type="text" class="form-control form-control-custom formula-input" value="${formula}" ${isF ? '' : 'disabled'} placeholder="เช่น: [A]/[B]*100">
                    <button class="btn btn-outline-secondary dropdown-toggle btn-formula-helper" type="button" data-bs-toggle="dropdown" aria-expanded="false" ${isF ? '' : 'disabled'} style="border-radius: 0 10px 10px 0;"><i class="fas fa-magic text-theme"></i> ตัวแปร</button>
                    <ul class="dropdown-menu dropdown-menu-end shadow-sm" style="max-height: 250px; overflow-y: auto; border-radius: 12px;">
                        <li class="px-3 py-1 text-muted small fw-bold bg-light">เลือกตัวแปรเพื่อแทรกลงในสูตร</li>
                        <li><hr class="dropdown-divider"></li>
                        ${varMenuHtml}
                    </ul>
                </div>
            </div>
            <div class="col-1 text-center"><button class="btn btn-sm btn-outline-danger btn-delete-row"><i class="fas fa-trash"></i></button></div>
        </div>`);
    }

    $('#reportListGroup').on('click', 'a', function(e) {
        e.preventDefault(); $('#reportListGroup a').removeClass('active fw-bold').addClass('text-muted').css({'background':'', 'border-color':''});
        $(this).removeClass('text-muted').addClass('active fw-bold').css({'background':'var(--primary-color)', 'border-color':'var(--primary-color)', 'color':'white'});
        let repName = $(this).data('report'); 
        let cat = $(this).data('category');
        $('#newReportForm').slideUp(); 
        $('#builderTitle').html(`แก้ไขโครงสร้าง: <span id="currentReportName" class="text-theme">${repName}</span>`);
        $('#btnDeleteSchema').show(); 
        $('#tableSchemaContainer').empty(); 

        let conf = existingSchemas[repName] ? existingSchemas[repName].config : {};

        if(cat === 'summary') {
            $('#schemaFieldsArea').hide();
            for(let i=1; i<=4; i++) {
                $(`#kpi${i}_col`).html('<option value="w_pct">น้ำเกินมาตรฐาน (%)</option><option value="d_pct">เด็กฟันตกกระ (%)</option><option value="red_zones">พื้นที่วิกฤต (Red Zones)</option><option value="safe_zones">พื้นที่ปลอดภัย (Safe Zones)</option><option value="w_tot">รวมแหล่งน้ำทั้งหมด</option><option value="d_scr">รวมเด็กที่ตรวจ (คน)</option><option value="d_flu">รวมเด็กพบฟันตกกระ (คน)</option>');
            }
        } else {
            $('#schemaFieldsArea').show();
            let schemaDef = existingSchemas[repName] ? existingSchemas[repName].fields : [];
            if(schemaDef && schemaDef.length > 0) { schemaDef.forEach(f => { createBuilderRow(f.name, f.db_ref, f.formula); }); } else { for(let i=0; i<3; i++) { createBuilderRow(); } }
            
            $('#chartPropCol').html(`<option value="${conf.proportion||''}">${conf.proportion||'-- ค่าเริ่มต้น --'}</option>`).val(conf.proportion||'');
            $('#chartDrillCol').html(`<option value="${conf.drilldown||''}">${conf.drilldown||'-- ค่าเริ่มต้น --'}</option>`).val(conf.drilldown||'');
            $('#chartMapCol').html(`<option value="${conf.map||''}">${conf.map||'-- ค่าเริ่มต้น --'}</option>`).val(conf.map||'');
            updateChartDropdowns();
        }
        
        // Load alert threshold
        $('#mapAlertThreshold').val(conf.alert_threshold !== undefined && conf.alert_threshold !== null ? conf.alert_threshold : '');
        
        if(conf.kpis && conf.kpis.length === 4) {
            conf.kpis.forEach((kpi, idx) => {
                let i = idx + 1;
                $(`#kpi${i}_label`).val(kpi.label);
                $(`#kpi${i}_type`).val(kpi.type);
                $(`#kpi${i}_col`).val(kpi.col||'');
                $(`#kpi${i}_color`).val(kpi.color);
            });
        } else {
            for(let i=1; i<=4; i++) { $(`#kpi${i}_label`).val(''); $(`#kpi${i}_type`).val('count'); $(`#kpi${i}_col`).val(''); $(`#kpi${i}_color`).val('main'); }
        }

        $('#groupRulesContainer').empty();
        if(conf.proportion_rules && conf.proportion_rules.length > 0) {
            $('#enableGrouping').prop('checked', true); $('#groupingBuilder').show();
            conf.proportion_rules.forEach(r => createGroupRuleRow(r.op, r.val1, r.val2, r.label));
        } else { $('#enableGrouping').prop('checked', false); $('#groupingBuilder').hide(); }
    });

    $('#btnCreateNewReport').click(function() {
        $('#reportListGroup a').removeClass('active fw-bold text-muted').css({'background':'', 'border-color':''});
        $('#builderTitle').html('สร้างโครงสร้าง: <span id="currentReportName" class="text-success">รายงานใหม่</span>');
        $('#schemaFieldsArea').show();
        $('#newReportForm').slideDown(); $('#btnDeleteSchema').hide(); $('#tableSchemaContainer').empty(); for(let i=0; i<3; i++) { createBuilderRow(); }
        $('#chartPropCol, #chartDrillCol, #chartMapCol').html('<option value="">-- ไม่ใช้ / ค่าเริ่มต้น --</option>');
        $('#enableGrouping').prop('checked', false); $('#groupingBuilder').hide(); $('#groupRulesContainer').empty();
        $('#mapAlertThreshold').val('');
        for(let i=1; i<=4; i++) { $(`#kpi${i}_label`).val(''); $(`#kpi${i}_type`).val('count'); $(`#kpi${i}_col`).html('<option value="">-- ไม่ใช้ --</option>'); $(`#kpi${i}_color`).val('main'); }
    });

    $('#btnAddColumnMock').click(function() { createBuilderRow(); updateChartDropdowns(); });
    $(document).on('click', '.btn-delete-row', function() { $(this).closest('.table-builder-row').remove(); updateChartDropdowns(); });

    $('#btnSaveSchema').click(function() {
        let reportName = ""; let reportCategory = "";
        if ($('#newReportForm').is(':visible')) { reportName = $('#newReportNameInput').val().trim(); reportCategory = $('#newReportCategoryInput').val(); if(!reportName) return alert("กรุณาระบุชื่อรายงาน"); } 
        else { reportName = $('#currentReportName').text(); reportCategory = $('#reportListGroup a.active').data('category') || 'health'; }
        
        let schemaData = [];
        if(reportCategory !== 'summary') {
            $('#tableSchemaContainer .table-builder-row').each(function() { let colName = $(this).find('.col-name').val(); let dbRef = $(this).find('.db-col-sel').val() || ""; let formula = $(this).find('.formula-input').val() || ""; if(colName) { schemaData.push({ name: colName, type: dbRef === "f" ? "Formula" : "DB_Column", db_ref: dbRef === "f" ? "" : dbRef, formula: formula }); } });
            if(schemaData.length === 0) return alert("เพิ่มอย่างน้อย 1 ฟิลด์"); 
        }
        
        let groupingRules = [];
        if($('#enableGrouping').is(':checked')) {
            $('#groupRulesContainer .group-rule-row').each(function() { let op = $(this).find('.rule-op').val(); let v1 = $(this).find('.rule-val1').val(); let v2 = $(this).find('.rule-val2').val(); let lbl = $(this).find('.rule-label').val(); if(lbl && v1 !== '') { groupingRules.push({ op: op, val1: v1, val2: v2, label: lbl }); } });
        }

        let kpiData = [];
        for(let i=1; i<=4; i++) {
            kpiData.push({ label: $(`#kpi${i}_label`).val() || `KPI ${i}`, type: $(`#kpi${i}_type`).val(), col: $(`#kpi${i}_col`).val(), color: $(`#kpi${i}_color`).val() });
        }
        
        let alertVal = $('#mapAlertThreshold').val();
        let configData = { 
            proportion: $('#chartPropCol').val(), 
            proportion_rules: groupingRules, 
            drilldown: $('#chartDrillCol').val(), 
            map: $('#chartMapCol').val(), 
            alert_threshold: (alertVal !== "" && alertVal !== undefined && alertVal !== null) ? parseFloat(alertVal) : null,
            kpis: kpiData 
        };
        let payload = { report_name: reportName, category: reportCategory, schema_data: { fields: schemaData, config: configData } };
        
        let originalBtnText = $(this).html(); $(this).html('<i class="fas fa-spinner fa-spin"></i>').prop('disabled', true);

        fetch('/api/save_schema', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': sessionStorage.getItem('adminToken') || '' }, body: JSON.stringify(payload) })
        .then(res => { if(res.status === 401) throw new Error('Unauthorized'); return res.json(); })
        .then(data => { if(data.success) { alert('บันทึกสำเร็จ!'); location.reload(); } else { alert('Error: ' + data.message); } })
        .catch(err => { if(err.message === 'Unauthorized') alert('เซสชันหมดอายุ กรุณาเข้าสู่ระบบแอดมินใหม่'); })
        .finally(() => { $(this).html(originalBtnText).prop('disabled', false); });
    });

    $('#btnDeleteSchema').click(function() {
        let reportName = $('#currentReportName').text();
        if(confirm(`คุณต้องการลบรายงาน "${reportName}" อย่างถาวรใช่หรือไม่?`)) {
            fetch('/api/delete_schema', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': sessionStorage.getItem('adminToken') || '' }, body: JSON.stringify({ report_name: reportName }) })
            .then(res => { if(res.status === 401) throw new Error('Unauthorized'); return res.json(); }).then(data => { if(data.success) { alert('ลบสำเร็จ!'); location.reload(); } else { alert('Error: ' + data.message); } })
            .catch(err => { if(err.message === 'Unauthorized') alert('เซสชันหมดอายุ กรุณาเข้าสู่ระบบแอดมินใหม่'); });
        }
    });

    // ----------------------------------------------------
    // 5. Data Preprocessing & Table Generation
    // ----------------------------------------------------
    function preprocessDataForCharts(reportName) {
        let schema = existingSchemas[reportName] ? existingSchemas[reportName].fields : [];
        let rules = existingSchemas[reportName] && existingSchemas[reportName].config ? existingSchemas[reportName].config.proportion_rules : [];
        let propCol = existingSchemas[reportName] && existingSchemas[reportName].config ? existingSchemas[reportName].config.proportion : 'สถานการณ์';

        globalData.forEach(row => {
            schema.forEach(col => {
                let fieldName = col.name;
                if (col.db_ref === 'f' || col.type === 'Formula') {
                    try {
                        let calcStr = col.formula; let matches = calcStr.match(/\[(.*?)\]/g);
                        if (matches) { matches.forEach(m => { let fieldRaw = m.replace('[', '').replace(']', ''); let dbKey = apiToDbRefMap[fieldRaw] || fieldRaw; let val = row[dbKey] || 0; calcStr = calcStr.replace(m, val); }); }
                        let result = eval(calcStr); row[fieldName] = isFinite(result) ? parseFloat(result.toFixed(2)) : 0;
                    } catch(e) { row[fieldName] = 0; }
                } else {
                    let dbKey = apiToDbRefMap[col.db_ref] || col.db_ref; row[fieldName] = row[dbKey];
                }
            });
            
            let rawVal = row[propCol];
            let finalLabel = rawVal !== undefined && rawVal !== '' ? String(rawVal) : 'ไม่ระบุ';
            if(rules && rules.length > 0) {
                let numVal = parseFloat(rawVal); let isNum = !isNaN(numVal); let strVal = String(rawVal);
                for(let r of rules) {
                    if (r.op === '<' && isNum && numVal < parseFloat(r.val1)) { finalLabel = r.label; break; }
                    if (r.op === '<=' && isNum && numVal <= parseFloat(r.val1)) { finalLabel = r.label; break; }
                    if (r.op === '>' && isNum && numVal > parseFloat(r.val1)) { finalLabel = r.label; break; }
                    if (r.op === '>=' && isNum && numVal >= parseFloat(r.val1)) { finalLabel = r.label; break; }
                    if (r.op === 'between' && isNum && numVal >= parseFloat(r.val1) && numVal <= parseFloat(r.val2)) { finalLabel = r.label; break; }
                    if (r.op === '==' && strVal == String(r.val1)) { finalLabel = r.label; break; }
                    if (r.op === 'contains' && strVal.includes(String(r.val1))) { finalLabel = r.label; break; }
                }
            }
            row['_chart_group_label'] = finalLabel;
        });
    }

    function buildDynamicTable(reportName, dataArray) {
        let schema = existingSchemas[reportName] ? existingSchemas[reportName].fields : [];
        
        if ($.fn.DataTable.isDataTable('#dynamicDataTable')) { 
            $('#dynamicDataTable').DataTable().clear().destroy(); 
            $('#dynamicDataTable').empty(); 
        }
        
        if (schema.length === 0) { $('#dynamicDataTable').html('<thead><tr><th>ไม่มีโครงสร้างตาราง</th></tr></thead><tbody></tbody>'); return; }

        let zone = $('#filter-zone').val(), prov = $('#filter-province').val(), dist = $('#filter-district').val();
        let aggKey = 'เขตสุขภาพ', aggTitle = 'เขตสุขภาพ';
        if(dist !== 'ทั้งหมด') { aggKey = 'raw'; }
        else if(prov !== 'ทั้งหมด') { aggKey = 'อำเภอ'; aggTitle = 'อำเภอ'; }
        else if(zone !== 'ทั้งหมด') { aggKey = 'จังหวัด'; aggTitle = 'จังหวัด'; }

        let tableData = []; let columnsDef = []; let theadHtml = '<thead><tr>';

        if(aggKey === 'raw') {
            schema.forEach(col => {
                theadHtml += `<th>${col.name}</th>`;
                columnsDef.push({ 
                    data: col.name, name: col.name,
                    defaultContent: "-", 
                    type: ['เขตสุขภาพ', 'จังหวัด', 'อำเภอ', 'ตำบล'].includes(col.name) ? 'natural' : null,
                    className: ['บ้านเลขที่', 'หมู่ที่', 'ละติจูด', 'ลองจิจูด', 'แหล่งข้อมูล'].includes(col.name) ? 'none' : '',
                    render: function(d, t, r) {
                        let val = (col.type === 'Formula') ? (r[col.name] !== undefined ? r[col.name] : 0) : d;
                        if (col.db_ref === 'fluoride_level' && t === 'display') return `<span class="ppm-badge ${r['สถานการณ์'] === 'เกินมาตรฐาน' ? 'level-high' : 'level-normal'}">${val||0}</span>`;
                        if (['status', 'dean_index_status'].includes(col.db_ref) && t === 'display') return `<span class="badge bg-secondary">${val||'ไม่ระบุ'}</span>`;
                        if (col.type === 'Formula' && t === 'display') return `<span class="ppm-badge ${val > 30 ? 'level-high' : 'level-normal'}">${val||0}%</span>`;
                        return val;
                    }
                });
            });
            theadHtml += '<th>แผนที่</th></tr></thead>';
            columnsDef.push({ data: null, name: 'mapbtn', defaultContent: "-", orderable: false, render: (d, t, r) => { let lat = parseFloat(r['ละติจูด']||0); let lon = parseFloat(r['ลองจิจูด']||0); return (!isNaN(lat) && lat!==0) ? `<button class="btn btn-sm fly-to-btn" style="background:#f1f5f9; color:#0ea5e9; border-radius:8px;" data-lat="${lat}" data-lon="${lon}"><i class="fas fa-map-marker-alt"></i></button>` : '-'; } });
        } 
        else {
            let grouped = {};
            let skipCols = ['check_date', 'location_name', 'hospcode', 'hosp_name', 'status', 'dean_index_status', 'water_type', 'latitude', 'longitude', 'house_no', 'moo', 'remark', 'data_source'];
            
            dataArray.forEach(row => {
                let key = row[aggKey] || 'ไม่ระบุ';
                if(!grouped[key]) {
                    grouped[key] = { [aggTitle]: key };
                    schema.forEach(c => { if(c.type !== 'Formula' && !skipCols.includes(c.db_ref)) grouped[key][c.name] = 0; });
                }
                schema.forEach(c => {
                    if(c.type !== 'Formula' && !skipCols.includes(c.db_ref)) {
                        let val = parseFloat(row[c.name]) || 0; 
                        grouped[key][c.name] += val;
                    }
                });
            });
            
            tableData = Object.values(grouped).map(row => {
                schema.forEach(c => {
                    if(c.type === 'Formula') {
                        try {
                            let calcStr = c.formula; let matches = calcStr.match(/\[(.*?)\]/g);
                            if(matches) matches.forEach(m => { let fRaw = m.replace('[','').replace(']',''); calcStr = calcStr.replace(m, row[fRaw] || 0); });
                            let res = eval(calcStr); row[c.name] = isFinite(res) ? parseFloat(res.toFixed(2)) : 0;
                        } catch(e) { row[c.name] = 0; }
                    }
                });
                return row;
            });

            tableData.sort((a, b) => String(a[aggTitle] || '').localeCompare(String(b[aggTitle] || ''), 'th', { numeric: true }));

            theadHtml += `<th>${aggTitle}</th>`; 
            columnsDef.push({ data: aggTitle, name: aggTitle, defaultContent: "-", type: 'natural' });
            
            schema.forEach(c => {
                if(!skipCols.includes(c.db_ref)) {
                    theadHtml += `<th>${c.name}</th>`;
                    columnsDef.push({ 
                        data: c.name, name: c.name,
                        defaultContent: "-", 
                        render: function(d, t, r) {
                            if (c.type === 'Formula' && t === 'display') return `<span class="ppm-badge ${d > 30 ? 'level-high' : 'level-normal'}">${d||0}%</span>`; 
                            return d;
                        }
                    });
                }
            });
            theadHtml += '</tr></thead>';
        }

        // สร้าง Footer สำหรับยอดรวมประเทศ
        let tfootHtml = '<tfoot><tr>';
        if(aggKey !== 'raw') {
            tfootHtml += '<th class="text-end fw-bold" style="color:var(--text-main);">ผลรวม:</th>';
            let skipCols = ['check_date', 'location_name', 'hospcode', 'hosp_name', 'status', 'dean_index_status', 'water_type', 'latitude', 'longitude', 'house_no', 'moo', 'remark', 'data_source'];
            schema.forEach(c => { if(!skipCols.includes(c.db_ref)) tfootHtml += '<th></th>'; });
        } else {
            schema.forEach(c => { tfootHtml += '<th></th>'; });
            tfootHtml += '<th></th>';
        }
        tfootHtml += '</tr></tfoot>';

        $('#dynamicDataTable').html(theadHtml + tfootHtml);

        let dtConfig = {
            orderCellsTop: true,
            fixedHeader: true,
            pageLength: 10,
            responsive: true,
            autoWidth: false,
            dom: '<"d-flex justify-content-between"<"row"<"col-md-auto"l><"col-md-auto"B>>>rt<"d-flex justify-content-between"ip>',
            buttons: [
                { extend: 'copy', text: '<i class="fas fa-copy me-1"></i> Copy' },
                { extend: 'csv', text: '<i class="fas fa-file-csv me-1"></i> CSV', charset: 'utf-8', bom: true },
                { extend: 'print', text: '<i class="fas fa-print me-1"></i> Print' }
            ],
            columns: columnsDef,
            footerCallback: function(row, data, start, end, display) {
                let api = this.api();
                let totals = {};
                
                schema.forEach(c => {
                    let colIdx = columnsDef.findIndex(def => def.name === c.name);
                    if(colIdx !== -1 && c.type !== 'Formula') {
                        let dataList = api.column(colIdx).data().toArray().map(v => parseFloat(v) || 0);
                        let total = dataList.reduce((a, b) => a + b, 0);
                        let isAvgCol = c.db_ref === 'fluoride_level' || c.name.includes('เฉลี่ย') || c.name.includes('ร้อยละ') || c.name.includes('%');
                        let displayVal = isAvgCol ? (dataList.length > 0 ? (total / dataList.length).toFixed(3) : 0) : total.toLocaleString('en-US');
                        totals[c.name] = total;
                        $(api.column(colIdx).footer()).html(`<span class="fw-bold" style="color:var(--text-main);">${displayVal}</span>`);
                    }
                });

                schema.forEach(c => {
                    let colIdx = columnsDef.findIndex(def => def.name === c.name);
                    if(colIdx !== -1 && c.type === 'Formula') {
                        try {
                            let f = c.formula;
                            let matches = f.match(/\[(.*?)\]/g);
                            if (matches) matches.forEach(m => {
                                  let raw = m.replace('[','').replace(']','');
                                  f = f.replace(m, totals[raw] || 0);
                            });
                            let res = eval(f);
                            let finalVal = isFinite(res) ? res.toFixed(2) : 0;
                            $(api.column(colIdx).footer()).html(`<span class="ppm-badge bg-theme" style="color:white !important;">${finalVal}%</span>`);
                        } catch(e) {
                            $(api.column(colIdx).footer()).html('-');
                        }
                    }
                });
            }
        };

        if (aggKey === 'raw') {
            dtConfig.serverSide = true;
            dtConfig.processing = true;
            dtConfig.ajax = {
                url: '/api/table_data',
                type: 'POST',
                contentType: 'application/json',
                data: function(d) {
                    let orderColName = '';
                    if (d.order && d.order.length > 0) {
                        let colIdx = d.order[0].column;
                        orderColName = columnsDef[colIdx].name || '';
                    }
                    let payload = {
                        draw: d.draw,
                        start: d.start,
                        length: d.length,
                        search_value: d.search ? d.search.value : '',
                        order_column: orderColName,
                        order_direction: (d.order && d.order.length > 0) ? d.order[0].dir : 'asc',
                        type: reportName,
                        'ปี': $('#filter-year').val(),
                        'ภาค': $('#filter-region').val(),
                        'เขตสุขภาพ': $('#filter-zone').val(),
                        'จังหวัด': $('#filter-province').val(),
                        'อำเภอ': $('#filter-district').val(),
                        'ตำบล': $('#filter-subdistrict').val()
                    };
                    return JSON.stringify(payload);
                },
                dataSrc: function(json) {
                    return json.data;
                }
            };
        } else {
            dtConfig.serverSide = false;
            dtConfig.data = tableData;
        }

        $('#dynamicDataTable').DataTable(dtConfig);
    }

    // ----------------------------------------------------
    // 6. Map & Charts Render Core
    // ----------------------------------------------------
    let currentType = 'ทั้งหมด'; let isDental = false; let globalData = []; let activeChartConfig = {};
    let map = L.map('leafletMap', { maxBounds: [[5.0, 97.0], [21.0, 106.0]], maxBoundsViscosity: 1.0, minZoom: 5 }).setView([15.0, 100.0], 6); 
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { crossOrigin: true }).addTo(map); 
    let markersGroup = L.markerClusterGroup({ disableClusteringAtZoom: 12 }); 
    map.addLayer(markersGroup);
    
    let homeMap = null;
    let homeMarkersGroup = null;

    let proportionBarChart = new Chart(document.getElementById('proportionBarChart').getContext('2d'), { 
        type: 'bar', 
        data: { labels: [], datasets: [{ data: [] }] }, 
        options: { 
            indexAxis: 'y', 
            plugins: { 
                legend: { display: false }, 
                datalabels: { display: true, anchor: 'end', align: 'right', formatter: v => v.toFixed(1) + (isDental ? '%' : '') } 
            }, 
            scales: { 
                x: { beginAtZero: true, grid: { color: 'rgba(148, 163, 184, 0.1)' } }, 
                y: { grid: { display: false } } 
            }, 
            maintainAspectRatio: false 
        } 
    });

    let drilldownChart = new Chart(document.getElementById('drilldownChart').getContext('2d'), { 
        type: 'bar', 
        data: { labels: [], datasets: [{ data: [], backgroundColor: '#0ea5e9' }] }, 
        options: { 
            plugins: { 
                legend: { display: false }, 
                datalabels: { display: true, anchor: 'end', align: 'top', formatter: v => v + '%' } 
            }, 
            scales: { 
                x: { grid: { display: false } }, 
                y: { type: 'linear', beginAtZero: true, grid: { color: 'rgba(148, 163, 184, 0.1)' } } 
            }, 
            maintainAspectRatio: false 
        } 
    });

    let homeCorrelationCtx = document.getElementById('homeCorrelationChart').getContext('2d'); 
    let homeCorrelationChart = new Chart(homeCorrelationCtx, { 
        type: 'bar', 
        data: { 
            labels: [], 
            datasets: [ 
                { type: 'line', label: 'ร้อยละเด็กฟันตกกระ (%)', data: [], borderColor: '#8b5cf6', backgroundColor: '#8b5cf6', tension: 0.4, yAxisID: 'y1', borderWidth: 3, pointRadius: 4 }, 
                { type: 'bar', label: 'ค่าเฉลี่ยฟลูออไรด์ (mg/L)', data: [], backgroundColor: 'rgba(14, 165, 233, 0.2)', borderColor: '#0ea5e9', borderWidth: 1, borderRadius: 4, yAxisID: 'y' } 
            ] 
        }, 
        options: { 
            plugins: { 
                legend: { position: 'top', labels: { font: { family: 'Prompt' } } } 
            }, 
            scales: { 
                x: { grid: { display: false } }, 
                y: { type: 'linear', position: 'left', title: { display: true, text: 'ค่าฟลูออไรด์ (mg/L)' } }, 
                y1: { type: 'linear', position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'เด็กฟันตกกระ (%)' }, min: 0, max: 30 } 
            }, 
            maintainAspectRatio: false 
        } 
    });

    let homeDonutCtx = document.getElementById('homeDonutChart').getContext('2d'); 
    let homeDonutChart = new Chart(homeDonutCtx, { 
        type: 'doughnut', 
        data: { labels: [], datasets: [{ data: [], backgroundColor: ['#0ea5e9', '#f59e0b', '#8b5cf6'], borderWidth: 0 }] }, 
        options: { 
            plugins: { 
                legend: { position: 'bottom', labels: { font: { family: 'Prompt' } } } 
            }, 
            cutout: '65%', 
            maintainAspectRatio: false 
        } 
    });

    let legendControl = L.control({position: 'bottomright'});
    legendControl.onAdd = function (map) { 
        let div = L.DomUtil.create('div', 'info legend'); 
        div.id = 'choropleth-legend-box'; 
        div.innerHTML = `<b id="geo-level-text" style="display:block; margin-bottom:8px; font-size: 13px;">แผนที่ความเสี่ยง</b><i style="background:#ef4444"></i> ระดับรุนแรง<br><i style="background:#f59e0b"></i> ระดับปานกลาง<br><i style="background:#eab308"></i> ระดับอ่อน<br><i style="background:#84cc16"></i> ระดับอ่อนมาก<br><i style="background:#10b981"></i> ปกติ/ปลอดภัย<br><i style="background:#e2e8f0; border: 1px dashed #94a3b8;"></i> ไม่มีข้อมูล`; 
        return div; 
    };

    let legendAdded = false; let geoJsonData = null; let currentGeoLevel = 'province'; let actualGeoLevel = 'province'; let currentGeoUrl = ''; let geoJsonCache = {}; let choroplethLayer = null;

    function fetchGeoJsonWithLazyLoading(level) {
        let url = '/static/provinces.geojson'; 
        if(level === 'district') url = '/static/districts.geojson'; 
        else if(level === 'subdistrict') url = '/static/subdistricts.geojson';
        
        if (currentGeoUrl === url && geoJsonData) { actualGeoLevel = level; return Promise.resolve(); } 
        currentGeoUrl = url;
        if (geoJsonCache[url]) { actualGeoLevel = level; geoJsonData = geoJsonCache[url]; return Promise.resolve(); }
        
        return fetch(url).then(res => { if (!res.ok) throw new Error('File not found'); return res.json(); }).then(data => { actualGeoLevel = level; geoJsonCache[url] = data; geoJsonData = data; }).catch(err => { actualGeoLevel = 'province'; currentGeoUrl = '/static/provinces.geojson'; if(geoJsonCache[currentGeoUrl]) { geoJsonData = geoJsonCache[currentGeoUrl]; return Promise.resolve(); } else { return fetch(currentGeoUrl).then(r => r.ok ? r.json() : {}).then(d => { geoJsonCache[currentGeoUrl] = d; geoJsonData = d; }).catch(() => Promise.resolve()); } });
    }

    function getFeatureProp(p, keys) { let lowerP = {}; for (let k in p) lowerP[k.toLowerCase()] = p[k]; for (let i = 0; i < keys.length; i++) { let val = lowerP[keys[i].toLowerCase()]; if (val !== undefined && val !== null && String(val).trim() !== "") return String(val); } return ""; }
    function cleanName(name) { if(!name) return ""; let n = name.replace(/^(จังหวัด|จ\.|อำเภอ|อ\.|ตำบล|ต\.|เทศบาลนคร|เทศบาลเมือง|เทศบาลตำบล)/g, '').replace(/\s+/g, ''); if (n.startsWith('เมือง') && n.length > 5 && !['เมืองพล', 'เมืองจันทร์', 'เมืองสรวง', 'เมืองปาน'].includes(n)) return 'เมือง'; return n; }
    function getProvName(p) { return cleanName(getFeatureProp(p, ['pro_th', 'prov_th', 'prov_namt', 'name_1', 'pv_tn', 'name'])); }
    function getAmpName(p) { return cleanName(getFeatureProp(p, ['amp_th', 'amp_namt', 'name_2', 'ap_tn'])); }
    function getTamName(p) { return cleanName(getFeatureProp(p, ['tam_th', 'tam_namt', 'name_3', 'tb_tn'])); }
    function getPolygonColor(val) { if (val < 0) return '#e2e8f0'; if (val > 40) return '#ef4444'; if (val > 30) return '#f59e0b'; if (val > 20) return '#eab308'; if (val > 10) return '#84cc16'; return '#10b981'; }

    function isFeatureInSelectedFilters(feature) {
        let p = feature.properties; let fProv = getProvName(p); let fAmp = getAmpName(p); let sProv = $('#filter-province').val().replace(/\s+/g, ''); let sAmp = $('#filter-district').val().replace(/\s+/g, ''); let sReg = $('#filter-region').val(); let sZone = $('#filter-zone').val();
        if (sProv !== 'ทั้งหมด' && fProv && fProv !== sProv) return false;
        if (sAmp !== 'ทั้งหมด' && fAmp) { let cleanSAmp = sAmp.replace(/^เมือง.*/, 'เมือง'); if (fAmp !== cleanSAmp) return false; }
        if (sProv === 'ทั้งหมด' && (sReg !== 'ทั้งหมด' || sZone !== 'ทั้งหมด')) { let allowedProvinces = []; $('#filter-province option').each(function() { let v = $(this).val(); if (v !== 'ทั้งหมด') allowedProvinces.push(v.replace(/\s+/g, '')); }); if (fProv && !allowedProvinces.includes(fProv)) return false; }
        return true;
    }

    function getFilteredAreaData(feature, checkedStatuses) {
        let areaName = (actualGeoLevel === 'subdistrict' ? getTamName(feature.properties) : (actualGeoLevel === 'district' ? getAmpName(feature.properties) : getProvName(feature.properties)));
        if (!areaName) return []; 
        return globalData.filter(d => { let dbName = (actualGeoLevel === 'subdistrict' ? d.ตำบล : (actualGeoLevel === 'district' ? d.อำเภอ : d.จังหวัด)) || ""; dbName = dbName.replace(/\s+/g, ''); if (actualGeoLevel === 'district' && dbName.startsWith('เมือง') && dbName.length > 5 && !['เมืองพล', 'เมืองจันทร์', 'เมืองสรวง', 'เมืองปาน'].includes(dbName)) dbName = 'เมือง'; let matchArea = dbName === areaName; return matchArea && checkedStatuses.includes(d['_chart_group_label']); });
    }

    function styleArea(feature) {
        if (!isFeatureInSelectedFilters(feature)) return { weight: 0, fillOpacity: 0, opacity: 0, interactive: false }; 
        let checkedStatuses = $('.map-layer-toggle:checked:visible').map(function(){ return $(this).val(); }).get();
        let areaData = getFilteredAreaData(feature, checkedStatuses); 
        if (areaData.length === 0) return { fillColor: '#f1f5f9', weight: 1.5, opacity: 1, color: '#cbd5e1', dashArray: '4,4', fillOpacity: 0.6 };
        let mapCol = activeChartConfig.map || 'ร้อยละเด็กฟันตกกระ'; let sum = 0; let count = 0;
        areaData.forEach(d => { let v = parseFloat(d[mapCol]); if(!isNaN(v)){ sum+=v; count++; } });
        let avg = count > 0 ? (sum/count) : 0;
        return { fillColor: getPolygonColor(avg), weight: 1.5, opacity: 1, color: '#fff', dashArray: '', fillOpacity: 0.85 };
    }

    function onEachArea(feature, layer) {
        if (!isFeatureInSelectedFilters(feature)) return; 
        let checkedStatuses = $('.map-layer-toggle:checked:visible').map(function(){ return $(this).val(); }).get(); let areaData = getFilteredAreaData(feature, checkedStatuses); let areaName = actualGeoLevel === 'subdistrict' ? getTamName(feature.properties) : (actualGeoLevel === 'district' ? getAmpName(feature.properties) : getProvName(feature.properties)); areaName = areaName || "ไม่ระบุ";
        let mapCol = activeChartConfig.map || 'ร้อยละเด็กฟันตกกระ'; let sum = 0; let count = 0;
        areaData.forEach(d => { let v = parseFloat(d[mapCol]); if(!isNaN(v)){ sum+=v; count++; } });
        let avg = count > 0 ? (sum/count) : 0; let avgText = count > 0 ? avg.toFixed(2) : "ไม่มีข้อมูลตามที่กรอง";
        let lvlPrefix = actualGeoLevel === 'province' ? 'จังหวัด' : (actualGeoLevel === 'district' ? 'อำเภอ' : 'ตำบล');
        let popupContent = `<div style="text-align:center; min-width: 160px; font-family:'Prompt', sans-serif;"><b style="font-size: 16px; color:var(--primary-color);">${lvlPrefix}${areaName}</b><hr style="margin:8px 0; border-color:#e2e8f0;"><div style="padding:6px; background:#f8fafc; border-radius:8px; border:1px solid #e2e8f0;">ค่าเฉลี่ย ${mapCol}: <br><span style="font-size:16px; font-weight:700; color: ${getPolygonColor(avg)};">${avgText}</span></div></div>`;
        layer.bindPopup(popupContent);
        layer.on({ mouseover: function(e){ let tgt = e.target; tgt.setStyle({ weight: 3, color: '#334155', fillOpacity: 0.95 }); tgt.bringToFront(); }, mouseout: function(e){ choroplethLayer.resetStyle(e.target); } });
    }

    function showLoading() { $('#loading-overlay').css('display', 'flex'); }
    function hideLoading() { $('#loading-overlay').hide(); }

    function shouldBlink(p, isWaterCategory) {
        let mapCol = activeChartConfig.map;
        let val = NaN;
        if (mapCol && p[mapCol] !== undefined) {
            val = parseFloat(p[mapCol]);
        } else {
            val = isWaterCategory 
                ? parseFloat(p['ปริมาณฟลูออไรด์'] || p['fluoride_level'] || p['ปริมาณฟลูออไรด์ (mg/L)'] || 0)
                : parseFloat(p['ร้อยละเด็กฟันตกกระ'] || p['pct_fluorosis'] || 0);
        }
        
        let threshold = activeChartConfig.alert_threshold !== undefined && activeChartConfig.alert_threshold !== null ? parseFloat(activeChartConfig.alert_threshold) : NaN;
        
        if (!isNaN(threshold)) {
            return (!isNaN(val) && val >= threshold);
        }
        
        // Default fallback rules if no alert threshold is defined
        if (isWaterCategory) {
            let statusVal = String(p['สถานการณ์'] || p['status'] || p['_chart_group_label'] || '').trim();
            return statusVal.includes('เกินมาตรฐาน') || statusVal.includes('ไม่ผ่าน') || (!isNaN(val) && val > 0.7);
        }
        
        // Dental default: blink if pct_fluorosis >= 10.0%
        let statusVal = String(p['สถานการณ์'] || p['status'] || p['_chart_group_label'] || '').trim();
        return statusVal.includes('วิกฤต') || statusVal.includes('รุนแรง') || (!isNaN(val) && val >= 10.0);
    }

    function createMarker(p, isWaterCategory, statusVal, lat, lon) {
        let isBlinking = shouldBlink(p, isWaterCategory);
        let iconHtml = '';
        if (isBlinking) {
            iconHtml = isWaterCategory
                ? `<div class="alert-sonar-marker"><i class="fas fa-tint"></i></div>`
                : `<div class="alert-sonar-marker sonar-dental"><i class="fas fa-tooth"></i></div>`;
        } else {
            let statusClass = statusVal.includes('เกิน') || statusVal.includes('ไม่ผ่าน') ? 'marker-red' : (statusVal.includes('ปกติ') || statusVal.includes('ผ่าน') ? 'marker-green' : 'marker-blue');
            iconHtml = `<div class="custom-marker ${statusClass}"><div class="marker-dot"></div></div>`;
        }
        
        let customIcon = L.divIcon({
            className: '',
            html: iconHtml,
            iconSize: [20, 20],
            iconAnchor: [10, 10]
        });
        
        let name = p.สถานที่ || p.สถานที่เก็บ || p.ชื่อหน่วยบริการ || 'จุดตรวจ';
        let mapCol = activeChartConfig.map;
        let valForDrawer = NaN;
        if (mapCol && p[mapCol] !== undefined) {
            valForDrawer = p[mapCol];
        } else {
            valForDrawer = isWaterCategory ? (p['ปริมาณฟลูออไรด์'] || 0) : (p['ร้อยละเด็กฟันตกกระ'] || 0);
        }
        
        let detailText = isWaterCategory 
            ? `ปริมาณฟลูออไรด์ ${valForDrawer} mg/L` 
            : `พบฟันตกกระ ${parseInt(p['พบฟันตกกระ'] || 0)} จาก ${parseInt(p['จำนวนตรวจ'] || 0)} ราย (${valForDrawer}%)`;
            
        let popupHtml = `
            <div class="p-1" style="font-family:'Prompt', sans-serif; min-width: 180px;">
                <h6 class="fw-bold m-0 text-slate-800" style="font-size: 0.9rem;">${name}</h6>
                <span class="badge ${isWaterCategory ? 'bg-danger' : 'bg-primary'} mb-2 mt-1" style="font-size:0.7rem;">${isWaterCategory ? 'แหล่งน้ำ' : 'สภาวะสุขภาพ'}</span>
                <div class="small text-muted mb-1"><b>ที่ตั้ง:</b> ต.${p.ตำบล || '-'} อ.${p.อำเภอ || '-'} จ.${p.จังหวัด || '-'}</div>
                <div class="small text-theme"><b>กลุ่ม:</b> ${statusVal}</div>
                <button class="btn btn-sm btn-primary-modern w-100 mt-2 px-2 py-1 open-drawer-btn" 
                    data-name="${name}" 
                    data-lat="${lat}" 
                    data-lng="${lon}" 
                    data-type="${isWaterCategory ? 'water' : 'dental'}" 
                    data-prov="${p.จังหวัด || '-'}" 
                    data-dist="${p.อำเภอ || '-'}" 
                    data-subdist="${p.ตำบล || '-'}" 
                    data-val="${valForDrawer}" 
                    data-status="${statusVal}"
                    data-detail="${detailText}"
                    style="font-size: 0.75rem; border-radius: 8px;">
                    ดูข้อมูลเชิงลึก <i class="fas fa-arrow-right ms-1"></i>
                </button>
            </div>
        `;
        return L.marker([lat, lon], {icon: customIcon}).bindPopup(popupHtml);
    }

    function updateMapDisplay() {
        if (choroplethLayer) { map.removeLayer(choroplethLayer); choroplethLayer = null; }
        markersGroup.clearLayers(); let bounds = [];
        let counts = {};
        globalData.forEach(p => { let val = p['_chart_group_label']; counts[val] = (counts[val] || 0) + 1; });
        
        let labels = Object.keys(counts); let dataChart = Object.values(counts);
        let palette = ['#10b981', '#ef4444', '#f59e0b', '#3b82f6', '#8b5cf6', '#f97316', '#14b8a6', '#f43f5e', '#64748b'];
        let bgColors = labels.map((l, i) => {
            if(l.includes('ปกติ') || l === 'ผ่าน' || l === 'ปลอดภัย') return '#10b981';
            if(l.includes('เกิน') || l.includes('รุนแรง') || l === 'ไม่ผ่าน') return '#ef4444';
            if(l.includes('ปานกลาง') || l.includes('อ่อน') || l.includes('เฝ้าระวัง')) return '#f59e0b';
            return palette[i % palette.length];
        });

        proportionBarChart.data.labels = labels; proportionBarChart.data.datasets[0].data = dataChart; proportionBarChart.data.datasets[0].backgroundColor = bgColors; proportionBarChart.update();

        let legendHtml = ''; labels.forEach((l, i) => { legendHtml += `<label class="d-flex align-items-center"><input class="form-check-input map-layer-toggle me-2" type="checkbox" value="${l}" checked> <span style="color:${bgColors[i]}; font-weight:600;">${l}</span></label>`; });
        $('#legend-dynamic').html('<div class="d-flex flex-wrap gap-3">' + legendHtml + '</div>');

        let checkedStatuses = $('.map-layer-toggle:checked:visible').map(function(){ return $(this).val(); }).get();
        let isWaterCategory = (existingSchemas[currentType] ? existingSchemas[currentType].category === 'env' : false);

        if(activeChartConfig.map && !isWaterCategory) {
            if(!legendAdded) { legendControl.addTo(map); legendAdded = true; } 
            if(geoJsonData && Object.keys(geoJsonData).length > 0) {
                let activeBounds = L.latLngBounds(); let hasVisibleFeature = false;
                choroplethLayer = L.geoJSON(geoJsonData, { style: styleArea, onEachFeature: function(f, l) { if (isFeatureInSelectedFilters(f)) { onEachArea(f, l); hasVisibleFeature = true; if(l.getBounds) activeBounds.extend(l.getBounds()); } } }).addTo(map);
                
                if (hasVisibleFeature && activeBounds.isValid()) map.flyToBounds(activeBounds, {padding: [30, 30]}); else map.flyTo([15.0, 100.0], 6);
            }
        } else {
            if(legendAdded) { map.removeControl(legendControl); legendAdded = false; } 
            globalData.forEach(p => {
                let statusVal = p['_chart_group_label'];
                if(checkedStatuses.includes(statusVal)) {
                    let lat = parseFloat(p['ละติจูด']); let lon = parseFloat(p['ลองจิจูด']);
                    if (!isNaN(lat) && !isNaN(lon) && lat !== 0) {
                        let marker = createMarker(p, isWaterCategory, statusVal, lat, lon);
                        markersGroup.addLayer(marker); bounds.push([lat, lon]);
                    }
                }
            });
            if (bounds.length > 0) map.flyToBounds(bounds, {padding: [30, 30]}); else map.flyTo([15.0, 100.0], 6);
        }
    }

    function updateDrilldownChart() {
        let groupKey = 'เขตสุขภาพ'; let p = $('#filter-province').val(); let d = $('#filter-district').val(); let r = $('#filter-region').val(); let z = $('#filter-zone').val(); let sd = $('#filter-subdistrict').val();
        if (d !== 'ทั้งหมด' || sd !== 'ทั้งหมด') { groupKey = 'ชื่อหน่วยบริการ'; } else if (p !== 'ทั้งหมด') { groupKey = 'อำเภอ'; } else if (r !== 'ทั้งหมด' || z !== 'ทั้งหมด') { groupKey = 'จังหวัด'; } else { groupKey = 'เขตสุขภาพ'; }
        let drillCol = activeChartConfig.drilldown; let checkedStatuses = $('.map-layer-toggle:checked:visible').map(function(){ return $(this).val(); }).get(); let grouped = {}; 
        globalData.forEach(row => {
            let statusVal = row['_chart_group_label'];
            if (checkedStatuses.includes(statusVal)) {
                let key = row[groupKey] || row['สถานที่'] || 'ไม่ระบุ'; if (!grouped[key]) grouped[key] = { sum: 0, count: 0 };
                if (drillCol && row[drillCol] !== undefined) { let v = parseFloat(row[drillCol]); if(!isNaN(v)) { grouped[key].sum += v; grouped[key].count += 1; } } else { grouped[key].count += 1; }
            }
        });
        let sortedKeys = Object.keys(grouped).sort((a, b) => {
            let valA = drillCol ? (grouped[a].count>0?grouped[a].sum/grouped[a].count:0) : grouped[a].count;
            let valB = drillCol ? (grouped[b].count>0?grouped[b].sum/grouped[b].count:0) : grouped[b].count;
            return valB - valA;
        });
        let labels = []; let values = []; 
        sortedKeys.forEach(k => { labels.push(k); let val = drillCol ? (grouped[k].count>0?grouped[k].sum/grouped[k].count:0) : grouped[k].count; values.push(parseFloat(val.toFixed(2))); });
        drilldownChart.data.labels = labels; drilldownChart.data.datasets[0].data = values; drilldownChart.data.datasets[0].backgroundColor = '#0ea5e9'; drilldownChart.options.scales.y.title.text = drillCol ? `ค่าเฉลี่ย ${drillCol}` : 'จำนวน (Count)'; $('#title-drilldown').html(`<i class="fas fa-chart-bar me-2 text-theme"></i> ${drillCol ? `ค่าเฉลี่ย ${drillCol}` : 'จำนวนข้อมูล'} แยกตาม ${groupKey}`); drilldownChart.update();
    }

    function loadData() {
        showLoading(); 
        let filters = { 'type': currentType, 'ปี': $('#filter-year').val(), 'ภาค': $('#filter-region').val(), 'เขตสุขภาพ': $('#filter-zone').val(), 'จังหวัด': $('#filter-province').val(), 'อำเภอ': $('#filter-district').val(), 'ตำบล': $('#filter-subdistrict').val() };

        if (currentType === 'AI ทำนายความเสี่ยง') {
            $('#homeDashboardView').hide();
            $('#spatialDashboardView').hide();
            $('#investigationReportView').hide();
            $('#aiPredictionView').show();
            $('body').removeClass('theme-home theme-dental');
            loadAIPredictions();
            hideLoading();
            return;
        }

        if (currentType === 'รายงานสอบสวนโรคฟันตกกระ') {
            $('#homeDashboardView').hide();
            $('#spatialDashboardView').hide();
            $('#aiPredictionView').hide();
            $('#investigationReportView').show();
            $('body').removeClass('theme-home theme-dental');
            
            let mailtoUrl = "mailto:efluoride.project@moph.go.th" +
                "?subject=" + encodeURIComponent("[รายงานสอบสวนโรค] พบเคสฟันตกกระ K00.3") +
                "&body=" + encodeURIComponent(
                    "เรียน โครงการเฝ้าระวังฟันตกกระ (efluoride.project@moph.go.th)\n\n" +
                    "เรื่อง: นำส่งรายงานสอบสวนโรคฟันตกกระ\n\n" +
                    "ข้าพเจ้า (ชื่อ-นามสกุล/ตำแหน่ง): ........................................\n" +
                    "หน่วยบริการ: ........................................\n" +
                    "เบอร์โทรศัพท์: ........................................\n\n" +
                    "ขอรายงานสรุปเคสโรคฟันตกกระ (K00.3) ดังต่อไปนี้:\n" +
                    "1. วันที่พบเคส/สอบสวนโรค: ........................................\n" +
                    "2. ข้อมูลผู้ป่วย: เพศ [  ] ชาย  [  ] หญิง  อายุ ............ ปี\n" +
                    "3. ระดับความรุนแรงของฟันตกกระ (Dean's Index/ระดับ): ........................................\n" +
                    "4. แหล่งน้ำบริโภคหลักของครัวเรือน: ........................................\n" +
                    "5. ระยะเวลาที่บริโภคน้ำจากแหล่งนี้ (ปี): ........................................\n" +
                    "6. รายละเอียดเพิ่มเติม: ................................................................................\n\n" +
                    "จึงเรียนมาเพื่อทราบและดำเนินการในระบบต่อไป"
                );
            $('#btnSendInvestigationMainEmail').attr('href', mailtoUrl);
            
            hideLoading();
            return;
        }

        if (currentType === 'ทั้งหมด') { 
            $('#homeDashboardView').show(); $('#spatialDashboardView').hide(); $('#aiPredictionView').hide(); $('#investigationReportView').hide(); $('body').addClass('theme-home').removeClass('theme-dental'); 
            setTimeout(() => { if (homeMap) homeMap.invalidateSize(); }, 200); 
            fetch('/api/data', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(filters) })
            .then(res => res.json()).then(data => {
                if(data.home_kpis_dynamic && data.home_kpis_dynamic.length > 0) {
                    let kpiHtml = '';
                    data.home_kpis_dynamic.forEach(k => {
                        let borderColors = {'danger': '#ef4444', 'theme': '#8b5cf6', 'warning': '#f59e0b', 'success': '#10b981', 'main': '#0f172a'};
                        let textColors = {'danger': 'text-danger', 'theme': 'text-theme', 'warning': 'text-warning', 'success': 'text-success', 'main': 'text-dark'};
                        let bColor = borderColors[k.color] || borderColors['main'];
                        let tColor = textColors[k.color] || textColors['main'];
                        if(k.color === 'theme') tColor = 'text-theme';
                        
                        let extraUnit = (k.col === 'red_zones' || k.col === 'safe_zones') ? '<span style="font-size: 1rem; font-weight: 500; color: #64748b;">จังหวัด</span>' : '';
                        kpiHtml += `<div class="col-md-3"><div class="kpi-card" style="border-left: 4px solid ${bColor} !important;"><div class="kpi-label">${k.label}</div><div class="kpi-value ${tColor}">${k.value} ${extraUnit}</div></div></div>`;
                    });
                    $('#homeKPIsContainer').html(kpiHtml);
                } else {
                    $('#homeKPIsContainer').html('<div class="col-12"><div class="alert alert-warning">ยังไม่ได้ตั้งค่าโครงสร้าง KPI สำหรับหน้าหลัก กรุณาตั้งค่าผ่านเมนูแอดมิน</div></div>');
                }

                homeDonutChart.data.labels = data.home_charts.donut.labels; homeDonutChart.data.datasets[0].data = data.home_charts.donut.data; homeDonutChart.update(); homeCorrelationChart.data.labels = data.home_charts.corr.labels; homeCorrelationChart.data.datasets[0].data = data.home_charts.corr.line; homeCorrelationChart.data.datasets[1].data = data.home_charts.corr.bar; homeCorrelationChart.update();
                let alertsHtml = '';
                data.top_alerts.forEach((alert, i) => {
                    let rankStyle = i < 3 
                        ? 'background: #fee2e2; color: #ef4444; border: 1px solid #fca5a5;' 
                        : 'background: #ffedd5; color: #f97316; border: 1px solid #fed7aa;';
                        
                    // Look up province centroid coordinate from critical_points
                    let provPoint = data.critical_points.find(cp => cp.prov === alert.prov);
                    let lat = provPoint ? provPoint.lat : 13.0;
                    let lng = provPoint ? provPoint.lng : 101.5;

                    alertsHtml += `
                        <div class="top-alert-row d-flex justify-content-between align-items-center p-3 border-bottom hover-bg-light transition-all cursor-pointer" 
                             data-lat="${lat}" data-lng="${lng}" style="transition: all 0.2s; cursor: pointer;">
                            <div class="d-flex align-items-center gap-3">
                                <div class="top-alert-rank d-flex align-items-center justify-content-center fw-bold rounded-circle" style="width: 36px; height: 36px; font-size: 0.95rem; min-width: 36px; ${rankStyle}">
                                    ${i+1}
                                </div>
                                <div>
                                    <h6 class="m-0 fw-bold text-slate-800" style="font-size: 0.95rem;">จ. ${alert.prov}</h6>
                                    <span class="small text-muted"><i class="fas fa-map-marker-alt text-danger me-1"></i>เขตสุขภาพที่ ${alert.zone}</span>
                                </div>
                            </div>
                            <div class="d-flex align-items-center gap-3">
                                <div class="text-end">
                                    <div class="small fw-bold text-slate-700" style="font-size: 0.75rem;">น้ำเกินมาตรฐาน</div>
                                    <div class="h6 m-0 fw-bold ${i < 3 ? 'text-danger' : 'text-warning'}">${alert.pct}%</div>
                                </div>
                                <button class="btn btn-xs btn-outline-danger btn-fly-home-map p-0 d-flex align-items-center justify-content-center" 
                                        data-lat="${lat}" data-lng="${lng}" title="เล็งจุดวิกฤตบนแผนที่" 
                                        style="width: 32px; height: 32px; border-radius: 50%;" onclick="event.stopPropagation();">
                                    <i class="fas fa-crosshairs"></i>
                                </button>
                            </div>
                        </div>
                    `;
                });
                if(alertsHtml === '') alertsHtml = '<div class="p-3 text-center text-muted">ไม่มีข้อมูลเฝ้าระวัง</div>'; $('#topAlertsContainer').html(alertsHtml);
                updateHomeMap(data.critical_points);
                
                if (data.dropdowns) {
                    function updateSelect(id, options, currentValue) { 
                        let select = $(id); 
                        select.empty(); 
                        let currStr = String(currentValue); 
                        options.forEach(opt => { 
                            let isSelected = (String(opt) === currStr) ? 'selected' : ''; 
                            select.append(`<option value="${opt}" ${isSelected}>${opt === 'ทั้งหมด' ? '-- ทั้งหมด --' : opt}</option>`); 
                        }); 
                    }
                    updateSelect('#filter-year', data.dropdowns.years, $('#filter-year').val());
                    updateSelect('#filter-region', data.dropdowns.regions, $('#filter-region').val());
                    updateSelect('#filter-zone', data.dropdowns.zones, $('#filter-zone').val());
                    updateSelect('#filter-province', data.dropdowns.provinces, $('#filter-province').val());
                    updateSelect('#filter-district', data.dropdowns.districts, $('#filter-district').val());
                    updateSelect('#filter-subdistrict', data.dropdowns.subdistricts, $('#filter-subdistrict').val());
                    let p = $('#filter-province').val(); 
                    let d = $('#filter-district').val();
                    $('#filter-district').prop('disabled', p === 'ทั้งหมด'); 
                    $('#filter-subdistrict').prop('disabled', p === 'ทั้งหมด' || d === 'ทั้งหมด');
                }
            }).finally(() => hideLoading()); return; 
        }
        
        $('#homeDashboardView').hide(); $('#spatialDashboardView').show(); $('#aiPredictionView').hide(); $('#investigationReportView').hide(); $('#dynamicReportTitle').text(currentType);
        let cat = existingSchemas[currentType] ? existingSchemas[currentType].category : 'env'; 
        activeChartConfig = existingSchemas[currentType] ? existingSchemas[currentType].config : {proportion:'', drilldown:'', map:'', kpis:[]};
        isDental = (cat === 'health');
        if(isDental) { $('body').addClass('theme-dental').removeClass('theme-home'); } else { $('body').removeClass('theme-dental theme-home'); }
        
        $('#title-bar').html(`<i class="fas fa-chart-pie me-2 text-theme"></i> สัดส่วนข้อมูล: ${activeChartConfig.proportion || 'การจัดกลุ่ม'}`);
        setTimeout(() => { if(map) map.invalidateSize(); }, 200);

        let prevLevel = currentGeoLevel; if ($('#filter-subdistrict').val() !== 'ทั้งหมด') currentGeoLevel = 'subdistrict'; else if ($('#filter-district').val() !== 'ทั้งหมด') currentGeoLevel = 'subdistrict'; else if ($('#filter-province').val() !== 'ทั้งหมด') currentGeoLevel = 'district'; else currentGeoLevel = 'province';
        let geoPromise = Promise.resolve(); if(prevLevel !== currentGeoLevel || !geoJsonData) { geoPromise = fetchGeoJsonWithLazyLoading(currentGeoLevel); }
        let lvlTxt = currentGeoLevel === 'province' ? 'จังหวัด' : (currentGeoLevel === 'district' ? 'อำเภอ' : 'ตำบล'); $('#geo-level-text').text(`สถานะพื้นที่ (${lvlTxt})`);

        let apiPromise = fetch('/api/data', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(filters) }).then(res => res.json());

        Promise.all([geoPromise, apiPromise]).then(results => {
            let data = results[1]; globalData = data.table_data;
            
            preprocessDataForCharts(currentType);
            buildDynamicTable(currentType, globalData);

            let kpiConf = activeChartConfig.kpis || [];
            if(kpiConf.length === 4) {
                kpiConf.forEach((kpi, idx) => {
                    let i = idx + 1; $(`#kpi-label-${i}`).text(kpi.label || `KPI ${i}`); let val = 0;
                    if(kpi.type === 'count') { val = globalData.length; } 
                    else if(kpi.type === 'sum' || kpi.type === 'avg') { let sum = 0, cnt = 0; globalData.forEach(r => { let num = parseFloat(r[kpi.col]); if(!isNaN(num)) { sum+=num; cnt++; } }); val = kpi.type === 'sum' ? sum : (cnt > 0 ? sum/cnt : 0); }
                    let displayVal = val.toLocaleString('en-US', {maximumFractionDigits:2});
                    let colorClass = 'text-main'; if(kpi.color === 'theme') colorClass = 'text-theme'; if(kpi.color === 'danger') colorClass = 'text-danger'; if(kpi.color === 'success') colorClass = 'text-success'; if(kpi.color === 'warning') colorClass = 'text-warning';
                    $(`#kpi-val-${i}`).html(`<span class="${colorClass}">${displayVal}</span>`);
                });
            } else {
                $('#kpi-label-1').text('จำนวนรายการตรวจ'); $('#kpi-val-1').text(globalData.length);
                $('#kpi-label-2').text('จำนวนจุดข้อมูล'); $('#kpi-val-2').text(globalData.length);
                $('#kpi-label-3').text('อัตราเฉลี่ยตัวชี้วัด'); $('#kpi-val-3').text('0%');
                $('#kpi-label-4').text('อัตราความเสี่ยงเฝ้าระวัง'); $('#kpi-val-4').text('0%');
            }
            
            function updateSelect(id, options, currentValue) { let select = $(id); select.empty(); let currStr = String(currentValue); options.forEach(opt => { let isSelected = (String(opt) === currStr) ? 'selected' : ''; select.append(`<option value="${opt}" ${isSelected}>${opt === 'ทั้งหมด' ? '-- ทั้งหมด --' : opt}</option>`); }); }
            updateSelect('#filter-year', data.dropdowns.years, $('#filter-year').val()); updateSelect('#filter-region', data.dropdowns.regions, $('#filter-region').val()); updateSelect('#filter-zone', data.dropdowns.zones, $('#filter-zone').val()); updateSelect('#filter-province', data.dropdowns.provinces, $('#filter-province').val()); updateSelect('#filter-district', data.dropdowns.districts, $('#filter-district').val()); updateSelect('#filter-subdistrict', data.dropdowns.subdistricts, $('#filter-subdistrict').val());
            let p = $('#filter-province').val(); let d = $('#filter-district').val();
            $('#filter-district').prop('disabled', p === 'ทั้งหมด'); $('#filter-subdistrict').prop('disabled', p === 'ทั้งหมด' || d === 'ทั้งหมด');
            
            updateMapDisplay(); updateDrilldownChart();
        }).catch(err => { console.warn(err); globalData = []; buildDynamicTable(currentType, []); updateMapDisplay(); updateDrilldownChart(); }).finally(() => hideLoading());
    }

    $(document).on('click', '.menu-trigger', function(e) {
        e.preventDefault(); $('.menu-trigger').removeClass('active text-danger'); 
        $(`.menu-trigger[data-type="${$(this).data('type')}"]`).addClass('active');
        if(existingSchemas[$(this).data('type')] && existingSchemas[$(this).data('type')].category === 'health') { $(`.custom-tabs .nav-link[data-type="${$(this).data('type')}"]`).addClass('text-danger'); }
        currentType = $(this).data('type'); 
        logVisit(currentType, 'VIEW');
        loadData();
    });

    $(document).on('change', '.map-layer-toggle', function() { 
        let isWaterCategory = (existingSchemas[currentType] ? existingSchemas[currentType].category === 'env' : false);
        let checkedStatuses = $('.map-layer-toggle:checked:visible').map(function(){ return $(this).val(); }).get();
        
        if (choroplethLayer) { map.removeLayer(choroplethLayer); choroplethLayer = null; }
        markersGroup.clearLayers(); let bounds = [];

        if(activeChartConfig.map && !isWaterCategory) {
            if(geoJsonData && Object.keys(geoJsonData).length > 0) {
                let activeBounds = L.latLngBounds(); let hasVisibleFeature = false;
                choroplethLayer = L.geoJSON(geoJsonData, { style: styleArea, onEachFeature: function(f, l) { if (isFeatureInSelectedFilters(f)) { onEachArea(f, l); hasVisibleFeature = true; if(l.getBounds) activeBounds.extend(l.getBounds()); } } }).addTo(map);
                
                if (hasVisibleFeature && activeBounds.isValid()) map.flyToBounds(activeBounds, {padding: [30, 30]}); else map.flyTo([15.0, 100.0], 6);
            }
        } else {
            globalData.forEach(p => {
                let statusVal = p['_chart_group_label'];
                if(checkedStatuses.includes(statusVal)) {
                    let lat = parseFloat(p['ละติจูด']); let lon = parseFloat(p['ลองจิจูด']);
                    if (!isNaN(lat) && !isNaN(lon) && lat !== 0) {
                        let marker = createMarker(p, isWaterCategory, statusVal, lat, lon);
                        markersGroup.addLayer(marker); bounds.push([lat, lon]);
                    }
                }
            });
            if (bounds.length > 0) map.flyToBounds(bounds, {padding: [30, 30]}); else map.flyTo([15.0, 100.0], 6);
        }
        updateDrilldownChart(); 
    });
    
    $('#filter-year').change(loadData); 
    $('#filter-region').change(function() { $('#filter-zone, #filter-province, #filter-district, #filter-subdistrict').val('ทั้งหมด'); loadData(); });
    $('#filter-zone').change(function() { $('#filter-province, #filter-district, #filter-subdistrict').val('ทั้งหมด'); loadData(); }); 
    $('#filter-province').change(function() { $('#filter-district, #filter-subdistrict').val('ทั้งหมด'); loadData(); });
    $('#filter-district').change(function() { $('#filter-subdistrict').val('ทั้งหมด'); loadData(); }); 
    $('#filter-subdistrict').change(loadData);
    $('#btnResetFilters').click(function() { $('select[id^="filter-"]').val('ทั้งหมด'); loadData(); });
    $(document).on('click', '.fly-to-btn', function() { 
        if (currentType === 'ทั้งหมด') {
            homeMap.flyTo([$(this).data('lat'), $(this).data('lon')], 15);
        } else if (currentType === 'AI ทำนายความเสี่ยง') {
            if (aiMap) aiMap.flyTo([$(this).data('lat'), $(this).data('lon')], 15);
        } else {
            map.flyTo([$(this).data('lat'), $(this).data('lon')], 15);
        }
    });

    $(document).on('click', '.top-alert-row, .btn-fly-home-map', function(e) {
        let lat = parseFloat($(this).attr('data-lat'));
        let lng = parseFloat($(this).attr('data-lng'));
        if (lat && lng && lat !== 13.0 && homeMap) {
            homeMap.flyTo([lat, lng], 9);
        }
    });

    // Toggle Map Fullscreen
    $(document).on('click', '#btnToggleMapExpand', function() {
        let card = $('#leafletMapCard');
        card.toggleClass('map-fullscreen');
        if (card.hasClass('map-fullscreen')) {
            $(this).html('<i class="fas fa-compress"></i> ย่อหน้าต่าง');
        } else {
            $(this).html('<i class="fas fa-expand"></i> ขยายแผนที่');
        }
        setTimeout(() => { if (map) map.invalidateSize(); }, 350);
    });

    // Close detail drawer
    $('#btnCloseDrawer').click(function() {
        $('#detailDrawer').removeClass('open');
    });

    // Fly to point from drawer
    $(document).on('click', '#btnFlyToDrawerPoint', function() {
        let lat = parseFloat($(this).data('lat'));
        let lng = parseFloat($(this).data('lng'));
        if (currentType === 'ทั้งหมด') {
            homeMap.setView([lat, lng], 15);
        } else {
            map.setView([lat, lng], 15);
        }
    });

    // Open detail drawer on popup button click
    $(document).on('click', '.open-drawer-btn', function(e) {
        e.preventDefault();
        openDetailDrawer({
            name: $(this).data('name'),
            type: $(this).data('type'),
            prov: $(this).data('prov'),
            dist: $(this).data('dist'),
            subdist: $(this).data('subdist'),
            val: $(this).data('val'),
            status: $(this).data('status'),
            detail: $(this).data('detail'),
            lat: $(this).data('lat'),
            lng: $(this).data('lng')
        });
    });

    // Homepage Surveillance Map Renderer
    function updateHomeMap(criticalPoints) {
        let homeMapContainer = document.getElementById('homeMap');
        if (!homeMapContainer) return;
        
        if (!homeMap) {
            homeMap = L.map('homeMap', { maxBounds: [[5.0, 97.0], [21.0, 106.0]], maxBoundsViscosity: 1.0, minZoom: 5 }).setView([15.0, 100.0], 6);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { 
                crossOrigin: true,
                attribution: '&copy; OpenStreetMap contributors'
            }).addTo(homeMap);
            homeMarkersGroup = L.markerClusterGroup({ disableClusteringAtZoom: 12 });
            homeMap.addLayer(homeMarkersGroup);
        }
        
        homeMarkersGroup.clearLayers();
        let bounds = [];
        
        if (criticalPoints && criticalPoints.length > 0) {
            criticalPoints.forEach(p => {
                let lat = parseFloat(p.lat);
                let lng = parseFloat(p.lng);
                if (!isNaN(lat) && !isNaN(lng) && lat !== 0 && lng !== 0) {
                    let isWater = p.type === 'water';
                    let iconHtml = isWater
                        ? `<div class="alert-sonar-marker"><i class="fas fa-tint"></i></div>`
                        : `<div class="alert-sonar-marker sonar-dental"><i class="fas fa-tooth"></i></div>`;
                        
                    let customIcon = L.divIcon({
                        className: '',
                        html: iconHtml,
                        iconSize: [20, 20],
                        iconAnchor: [10, 10]
                    });
                    
                    let popupContent = `
                        <div class="p-1" style="font-family: 'Prompt', sans-serif; min-width: 200px;">
                            <h6 class="fw-bold m-0 text-slate-800" style="font-size: 0.95rem;">${p.name}</h6>
                            <span class="badge ${isWater ? 'bg-danger' : 'bg-primary'} mb-2 mt-1" style="font-size: 0.75rem;">${isWater ? 'แหล่งน้ำเกินมาตรฐาน' : 'เด็กฟันตกกระวิกฤต'}</span>
                            <div class="small text-muted mb-1"><b>ที่ตั้ง:</b> ต.${p.subdist} อ.${p.dist} จ.${p.prov}</div>
                            <div class="small text-theme"><b>ค่าที่พบ:</b> ${p.detail}</div>
                            <button class="btn btn-sm btn-primary-modern w-100 mt-2 px-2 py-1 open-drawer-btn" 
                                data-name="${p.name}" 
                                data-lat="${p.lat}" 
                                data-lng="${p.lng}" 
                                data-type="${p.type}" 
                                data-prov="${p.prov}" 
                                data-dist="${p.dist}" 
                                data-subdist="${p.subdist}" 
                                data-val="${p.val}" 
                                data-status="${p.status}"
                                data-detail="${p.detail}"
                                style="font-size: 0.75rem; border-radius: 8px;">
                                ดูข้อมูลเชิงลึก <i class="fas fa-arrow-right ms-1"></i>
                            </button>
                        </div>
                    `;
                    
                    let marker = L.marker([lat, lng], { icon: customIcon }).bindPopup(popupContent);
                    homeMarkersGroup.addLayer(marker);
                    bounds.push([lat, lng]);
                }
            });
            
            if (bounds.length > 0) {
                homeMap.fitBounds(bounds, { padding: [40, 40] });
            }
        }
        
        setTimeout(() => {
            homeMap.invalidateSize();
        }, 300);
    }

    // Slide-over details drawer opener
    function openDetailDrawer(data) {
        $('#drawerTitle').text(data.name);
        
        let bodyHtml = '';
        
        if (data.type === 'ai_prediction') {
            let val = parseFloat(data.val) || 0;
            let styleColor = '#10b981'; // green
            let badgeClass = 'bg-success';
            if (val > 15.0) {
                styleColor = '#ef4444'; // red
                badgeClass = 'bg-danger';
            } else if (val > 5.0) {
                styleColor = '#f97316'; // orange
                badgeClass = 'bg-warning text-dark';
            }

            let quadrantLabel = 'ไม่ระบุ';
            let quadColor = '#cbd5e1';
            let lisaQuad = parseInt(data.lisa_quad);
            let lisaP = parseFloat(data.lisa_p);
            
            if (!isNaN(lisaP) && lisaP < 0.05) {
                if (lisaQuad === 1) {
                    quadrantLabel = 'High-High (Hotspot)';
                    quadColor = '#ef4444';
                } else if (lisaQuad === 2) {
                    quadrantLabel = 'Low-High Outlier';
                    quadColor = '#06b6d4';
                } else if (lisaQuad === 3) {
                    quadrantLabel = 'Low-Low (Coldspot)';
                    quadColor = '#2563eb';
                } else if (lisaQuad === 4) {
                    quadrantLabel = 'High-Low Outlier';
                    quadColor = '#ec4899';
                }
            } else {
                quadrantLabel = 'ไม่มีนัยสำคัญเชิงพื้นที่ (Not Significant)';
                quadColor = '#cbd5e1';
            }
            
            bodyHtml = `
                <div class="mb-4 p-3 rounded" style="background: rgba(15, 23, 42, 0.05); color: #0f172a; border-left: 4px solid #475569;">
                    <div class="fw-bold"><i class="fas fa-brain text-theme me-2"></i>ผลลัพธ์ทำนายระดับความเสี่ยง</div>
                    <div class="small mt-1">วิเคราะห์เชิงทำนายโดยใช้แบบจำลองความสัมพันธ์ทางพื้นที่ (Spatial Model)</div>
                </div>
                
                <div class="mb-4">
                    <h6 class="fw-bold text-muted small uppercase mb-2">ระดับความเสี่ยงทำนาย (AI Predict Risk)</h6>
                    <div class="p-4 bg-white rounded border shadow-sm text-center">
                        <div class="risk-gauge-container">
                            <div class="risk-gauge" id="drawerRiskGauge" style="background: conic-gradient(${styleColor} ${val}%, #e2e8f0 ${val}%);">
                                <div class="risk-gauge-content">
                                    <div class="risk-gauge-value">${val.toFixed(2)}%</div>
                                    <div class="risk-gauge-label">Risk Index</div>
                                </div>
                            </div>
                        </div>
                        <div class="mt-2 fw-bold" style="color: ${styleColor}; font-size: 1.05rem;">${data.status}</div>
                        <div class="small text-muted mt-1" style="font-size: 0.75rem;">เกณฑ์: ต่ำ &lt; 5% | ปานกลาง 5% - 15% | สูง &gt; 15%</div>
                    </div>
                </div>

                <div class="mb-4">
                    <h6 class="fw-bold text-muted small uppercase mb-2">ความสัมพันธ์เชิงพื้นที่ (Spatial Autocorrelation)</h6>
                    <div class="p-3 bg-white rounded border shadow-sm">
                        <div class="mb-2 d-flex justify-content-between align-items-center">
                            <span class="small fw-bold text-slate-700">กลุ่มความสัมพันธ์ (LISA):</span>
                            <span class="badge px-2 py-1" style="background-color: ${quadColor}; color: ${(!isNaN(lisaP) && lisaP < 0.05) ? '#ffffff' : '#475569'}; font-size: 0.75rem; font-family: 'Prompt', sans-serif;">${quadrantLabel}</span>
                        </div>
                        <div class="mb-2 small text-slate-700"><b>Local Moran's I:</b> <span style="font-family: 'Outfit'; font-weight: 600;">${data.lisa_i !== undefined && !isNaN(parseFloat(data.lisa_i)) ? parseFloat(data.lisa_i).toFixed(4) : '-'}</span></div>
                        <div class="small text-slate-700"><b>ระดับนัยสำคัญ (p-value):</b> <span style="font-family: 'Outfit'; font-weight: 600; color: ${(!isNaN(lisaP) && lisaP < 0.05) ? '#10b981' : '#64748b'};">${data.lisa_p !== undefined && !isNaN(parseFloat(data.lisa_p)) ? parseFloat(data.lisa_p).toFixed(4) : '-'}</span> ${(!isNaN(lisaP) && lisaP < 0.05) ? '<i class="fas fa-check-circle text-success ms-1"></i>' : ''}</div>
                    </div>
                </div>
                
                <div class="mb-4">
                    <h6 class="fw-bold text-muted small uppercase mb-2">ตัวแปรวิเคราะห์เชิงพื้นที่ (Spatial Inputs)</h6>
                    <div class="p-3 bg-white rounded border shadow-sm">
                        <div class="row g-2">
                            <div class="col-6">
                                <div class="p-3 bg-light rounded border text-center">
                                    <div class="small text-muted fw-bold mb-1" style="font-size: 0.72rem;">ฟลูออไรด์เฉลี่ย</div>
                                    <div class="fs-5 fw-bold text-slate-800" style="font-family: 'Outfit';">${data.water_ppm !== undefined ? parseFloat(data.water_ppm).toFixed(3) : '-'} <span style="font-size: 0.75rem; font-weight: normal; color: #64748b;">ppm</span></div>
                                </div>
                            </div>
                            <div class="col-6">
                                <div class="p-3 bg-light rounded border text-center">
                                    <div class="small text-muted fw-bold mb-1" style="font-size: 0.72rem;">ฟันตกกระสะสม</div>
                                    <div class="fs-5 fw-bold text-slate-800" style="font-family: 'Outfit';">${data.cases !== undefined ? data.cases : '-'} <span style="font-size: 0.75rem; font-weight: normal; color: #64748b;">ราย</span></div>
                                </div>
                            </div>
                            <div class="col-12">
                                <div class="p-3 bg-light rounded border text-center">
                                    <div class="small text-muted fw-bold mb-1" style="font-size: 0.72rem;">สัดส่วนเคสรุนแรง (Severe Cases)</div>
                                    <div class="fs-5 fw-bold text-danger" style="font-family: 'Outfit';">${data.severe !== undefined ? data.severe : '-'} <span style="font-size: 0.75rem; font-weight: normal; color: #ef4444;">ราย</span></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="mb-4">
                    <h6 class="fw-bold text-muted small uppercase mb-2">ที่ตั้งพื้นที่และพิกัดแผนที่</h6>
                    <div class="p-3 bg-white rounded border shadow-sm">
                        <div class="mb-2"><b>อำเภอ:</b> ${data.dist}</div>
                        <div class="mb-2"><b>จังหวัด:</b> ${data.prov}</div>
                        <div><b>พิกัด GPS:</b> ${parseFloat(data.lat).toFixed(5)}, ${parseFloat(data.lng).toFixed(5)}</div>
                    </div>
                </div>
                
                <div class="d-flex gap-2 mt-4">
                    <button class="btn btn-primary-modern flex-grow-1" id="btnFlyToDrawerPoint" data-lat="${data.lat}" data-lng="${data.lng}" style="border-radius: 10px; padding: 12px;">
                        <i class="fas fa-crosshairs me-2"></i>นำทางไปจุดนี้
                    </button>
                </div>
            `;
        } else {
            let headerColor = data.type === 'water' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(139, 92, 246, 0.1)';
            let headerTextColor = data.type === 'water' ? '#ef4444' : '#8b5cf6';
            let badgeClass = data.type === 'water' ? 'bg-danger' : 'bg-primary';
            
            let progressPercent = 0;
            if (data.type === 'water') {
                progressPercent = Math.min(100, (parseFloat(data.val) / 2.0) * 100);
            } else {
                progressPercent = Math.min(100, parseFloat(data.val));
            }
            
            let gaugeLabel = data.type === 'water' ? 'ปริมาณฟลูออไรด์' : 'อัตราการเกิดฟันตกกระ';
            let gaugeValue = data.type === 'water' ? `${data.val} mg/L` : `${data.val}%`;
            let standardLabel = data.type === 'water' ? 'เกณฑ์มาตรฐาน: 0.7 mg/L' : 'เกณฑ์วิกฤต: >10%';
            
            bodyHtml = `
                <div class="mb-4 p-3 rounded" style="background: ${headerColor}; color: ${headerTextColor}; border-left: 4px solid ${headerTextColor};">
                    <div class="fw-bold"><i class="fas ${data.type === 'water' ? 'fa-tint' : 'fa-tooth'} me-2"></i>ข้อมูลเฝ้าระวังภัยพิบัติ</div>
                    <div class="small mt-1">${data.type === 'water' ? 'แหล่งน้ำธรรมชาติ/ประปา ที่มีฟลูออไรด์สูงกว่ามาตรฐาน' : 'พื้นที่พบผู้ป่วยเด็กฟันตกกระสูงผิดปกติ'}</div>
                </div>
                
                <div class="mb-4">
                    <h6 class="fw-bold text-muted small uppercase mb-2">ที่ตั้งสถานบริการ/จุดเก็บตัวอย่าง</h6>
                    <div class="p-3 bg-white rounded border shadow-sm">
                        <div class="mb-2"><b>ตำบล:</b> ${data.subdist}</div>
                        <div class="mb-2"><b>อำเภอ:</b> ${data.dist}</div>
                        <div class="mb-2"><b>จังหวัด:</b> ${data.prov}</div>
                        <div><b>พิกัด GPS:</b> ${parseFloat(data.lat).toFixed(5)}, ${parseFloat(data.lng).toFixed(5)}</div>
                    </div>
                </div>
                
                <div class="mb-4">
                    <h6 class="fw-bold text-muted small uppercase mb-2">ตัวชี้วัดความรุนแรง (Metrics)</h6>
                    <div class="p-3 bg-white rounded border shadow-sm">
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <span class="fw-bold" style="font-size: 0.85rem;">${gaugeLabel}</span>
                            <span class="fs-5 fw-bold" style="color: ${headerTextColor};">${gaugeValue}</span>
                        </div>
                        <div class="progress mb-2" style="height: 10px; border-radius: 5px; background-color: #e2e8f0;">
                            <div class="progress-bar" role="progressbar" 
                                 style="width: ${progressPercent}%; background-color: ${headerTextColor};" 
                                 aria-valuenow="${progressPercent}" aria-valuemin="0" aria-valuemax="100"></div>
                        </div>
                        <div class="d-flex justify-content-between small text-muted" style="font-size: 0.75rem;">
                            <span>0</span>
                            <span>${standardLabel}</span>
                        </div>
                    </div>
                </div>
                
                <div class="mb-4">
                    <h6 class="fw-bold text-muted small uppercase mb-2">สถานการณ์ปัจจุบัน</h6>
                    <div class="p-3 bg-white rounded border shadow-sm">
                        <div class="d-flex align-items-center gap-2 mb-2">
                            <span class="badge ${badgeClass} px-3 py-2" style="font-size: 0.8rem; border-radius: 6px;">${data.status}</span>
                        </div>
                        <p class="m-0 small text-muted">${data.detail}</p>
                    </div>
                </div>
                
                <div class="d-flex gap-2 mt-4">
                    <button class="btn btn-primary-modern flex-grow-1" id="btnFlyToDrawerPoint" data-lat="${data.lat}" data-lng="${data.lng}" style="border-radius: 10px; padding: 12px;">
                        <i class="fas fa-crosshairs me-2"></i>นำทางไปจุดนี้
                    </button>
                </div>
            `;
        }
        
        $('#drawerBody').html(bodyHtml);
        $('#detailDrawer').addClass('open');
    }

    // ----------------------------------------------------
    // 7. Security & Stats, ROPA, and Page Logging
    // ----------------------------------------------------
    function logVisit(pageName, actionType) {
        fetch('/api/log_visit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ page_name: pageName, action_type: actionType })
        }).catch(err => console.warn('Logging visit failed:', err));
    }

    let visitStatsChartInstance = null;

    function loadSecurityAndStats() {
        fetch('/api/get_stats', {
            method: 'GET',
            headers: { 'Authorization': sessionStorage.getItem('adminToken') || '' }
        })
        .then(res => {
            if(res.status === 401) throw new Error('Unauthorized');
            return res.json();
        })
        .then(data => {
            if (data.success) {
                // Render stats chart
                let ctx = document.getElementById('visitStatsChart').getContext('2d');
                let labels = data.visits.map(v => v.page_name);
                let counts = data.visits.map(v => v.count);
                
                if (visitStatsChartInstance) {
                    visitStatsChartInstance.destroy();
                }
                
                visitStatsChartInstance = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'จำนวนการเยี่ยมชม (Visits)',
                            data: counts,
                            backgroundColor: '#8b5cf6',
                            borderRadius: 6
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false }
                        },
                        scales: {
                            y: { beginAtZero: true, ticks: { stepSize: 1 } }
                        }
                    }
                });

                // Render admin table
                let adminsHtml = '';
                data.admins.forEach(admin => {
                    let deleteBtn = admin.username === 'admin'
                        ? '<span class="text-muted small">ระบบหลัก</span>'
                        : `<button class="btn btn-sm btn-outline-danger btn-delete-admin" data-username="${admin.username}"><i class="fas fa-trash-alt"></i> ลบ</button>`;
                    
                    adminsHtml += `
                        <tr>
                            <td class="ps-3 fw-bold text-slate-700">${admin.username}</td>
                            <td><span class="badge bg-light text-theme border">${admin.role}</span></td>
                            <td>${admin.created_at}</td>
                            <td class="text-center">${deleteBtn}</td>
                        </tr>
                    `;
                });
                $('#adminUsersTableBody').html(adminsHtml);
            }
        })
        .catch(err => {
            console.error('Error loading stats:', err);
            $('#adminUsersTableBody').html('<tr><td colspan="4" class="text-center text-danger">ปฏิเสธการเข้าถึง หรือเซสชันหมดอายุ</td></tr>');
        });
    }

    // Add admin credentials click handler
    $(document).on('click', '#btnAddAdmin', function() {
        let u = $('#newAdminUser').val().trim();
        let p = $('#newAdminPassword').val().trim();
        if (!u || !p) {
            alert('กรุณากรอกทั้งชื่อผู้ใช้งานและรหัสผ่าน');
            return;
        }
        
        fetch('/api/manage_admin', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': sessionStorage.getItem('adminToken') || ''
            },
            body: JSON.stringify({ action: 'add', username: u, password: p })
        })
        .then(res => {
            if(res.status === 401) throw new Error('Unauthorized');
            return res.json();
        })
        .then(data => {
            if(data.success) {
                alert('เพิ่ม/อัปเดตบัญชีแอดมินสำเร็จ');
                $('#newAdminUser').val('');
                $('#newAdminPassword').val('');
                loadSecurityAndStats();
            } else {
                alert('เกิดข้อผิดพลาด: ' + data.message);
            }
        })
        .catch(err => alert('ไม่สามารถทำรายการได้: ' + err.message));
    });

    // Delete admin credentials click handler
    $(document).on('click', '.btn-delete-admin', function() {
        let username = $(this).data('username');
        if (confirm(`คุณต้องการลบแอดมิน "${username}" หรือไม่?`)) {
            fetch('/api/manage_admin', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': sessionStorage.getItem('adminToken') || ''
                },
                body: JSON.stringify({ action: 'delete', username: username })
            })
            .then(res => {
                if(res.status === 401) throw new Error('Unauthorized');
                return res.json();
            })
            .then(data => {
                if(data.success) {
                    alert('ลบบัญชีแอดมินสำเร็จ');
                    loadSecurityAndStats();
                } else {
                    alert('เกิดข้อผิดพลาด: ' + data.message);
                }
            })
            .catch(err => alert('ไม่สามารถทำรายการได้: ' + err.message));
        }
    });

    function loadRopaLogs() {
        fetch('/api/get_stats', {
            method: 'GET',
            headers: { 'Authorization': sessionStorage.getItem('adminToken') || '' }
        })
        .then(res => {
            if(res.status === 401) throw new Error('Unauthorized');
            return res.json();
        })
        .then(data => {
            if (data.success) {
                let logsHtml = '';
                if(data.audit.length === 0) {
                    logsHtml = '<tr><td colspan="6" class="text-center text-muted">ไม่มีบันทึกประวัติกิจกรรม</td></tr>';
                } else {
                    data.audit.forEach(log => {
                        let badgeColor = log.action === 'LOGIN' ? 'bg-success' : (log.action.includes('DELETE') ? 'bg-danger' : 'bg-primary');
                        logsHtml += `
                            <tr>
                                <td class="ps-3 text-muted" style="font-size:0.8rem;">${log.timestamp}</td>
                                <td class="fw-bold">${log.username}</td>
                                <td><span class="badge ${badgeColor}">${log.action}</span></td>
                                <td><span class="text-slate-600">${log.target}</span></td>
                                <td style="max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${log.details}">${log.details}</td>
                                <td class="text-muted" style="font-size:0.8rem;">${log.ip_address}</td>
                            </tr>
                        `;
                    });
                }
                $('#ropaLogsTableBody').html(logsHtml);
            }
        })
        .catch(err => {
            console.error('Error loading ROPA logs:', err);
            $('#ropaLogsTableBody').html('<tr><td colspan="6" class="text-center text-danger">ปฏิเสธการเข้าถึง หรือเซสชันหมดอายุ</td></tr>');
        });
    }

    // Bind tab clicks in settings modal
    $('button[data-bs-toggle="pill"]').on('shown.bs.tab', function(e) {
        let targetId = $(e.target).attr('data-bs-target');
        if (targetId === '#settings-security-stats') {
            loadSecurityAndStats();
        } else if (targetId === '#settings-ropa-logs') {
            loadRopaLogs();
        } else if (targetId === '#settings-investigations') {
            loadInvestigations();
        }
    });

    let investigationsCache = {};

    function loadInvestigations() {
        $('#investigationsTableBody').html('<tr><td colspan="8" class="text-center text-muted py-3">กำลังโหลดรายงานสอบสวนโรค...</td></tr>');
        
        fetch('/api/investigation/list', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': sessionStorage.getItem('adminToken') || ''
            }
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                let html = '';
                investigationsCache = {};
                if (data.data.length === 0) {
                    html = '<tr><td colspan="8" class="text-center text-muted py-3">ไม่พบประวัติรายงานสอบสวนโรคในระบบ</td></tr>';
                } else {
                    data.data.forEach(item => {
                        investigationsCache[item.id] = item;
                        
                        let statusBadge = '';
                        if (item.status === 'Pending') {
                            statusBadge = '<span class="badge bg-warning text-dark">Pending</span>';
                        } else if (item.status === 'Investigating') {
                            statusBadge = '<span class="badge bg-primary">Investigating</span>';
                        } else {
                            statusBadge = '<span class="badge bg-success">Resolved</span>';
                        }

                        html += `
                            <tr>
                                <td class="ps-3">${item.investigation_date}</td>
                                <td>${item.hospcode}</td>
                                <td>${item.hosp_name}</td>
                                <td>เพศ ${item.patient_gender} / อายุ ${item.patient_age} ปี</td>
                                <td class="fw-bold text-danger">${item.severity_level}</td>
                                <td>${item.drinking_water_source}</td>
                                <td>${statusBadge}</td>
                                <td class="text-center">
                                    <button class="btn btn-xs btn-primary-modern btn-view-investigation py-0 px-2" style="font-size: 0.75rem;" data-id="${item.id}"><i class="fas fa-eye me-1"></i> ดูรายละเอียด</button>
                                </td>
                            </tr>
                        `;
                    });
                }
                $('#investigationsTableBody').html(html);
            } else {
                $('#investigationsTableBody').html(`<tr><td colspan="8" class="text-center text-danger py-3">เกิดข้อผิดพลาด: ${data.message || 'ปฏิเสธการเข้าถึง'}</td></tr>`);
            }
        })
        .catch(err => {
            console.error('Error loading investigations:', err);
            $('#investigationsTableBody').html('<tr><td colspan="8" class="text-center text-danger py-3">เกิดข้อผิดพลาดในการโหลดข้อมูล</td></tr>');
        });
    }

    $(document).on('click', '.btn-view-investigation', function() {
        let id = $(this).attr('data-id');
        let item = investigationsCache[id];
        if (!item) return;

        // Fill data in modal
        $('#det_hospcode').text(item.hospcode);
        $('#det_hosp_name').text(item.hosp_name);
        $('#det_investigation_date').text(item.investigation_date);
        $('#det_investigator_name').text(item.investigator_name || '-');
        $('#det_investigator_phone').text(item.investigator_phone || '-');
        
        $('#det_patient_gender').text(item.patient_gender || '-');
        $('#det_patient_age').text(item.patient_age || '0');
        $('#det_severity_level').text(item.severity_level);
        $('#det_drinking_water_source').text(item.drinking_water_source || '-');
        $('#det_exposure_years').text(item.exposure_years || '0');
        $('#det_created_at').text(item.created_at);
        $('#det_details').text(item.details || '-');

        // Create mailto link
        let projectEmail = "efluoride.project@moph.go.th";
        let subject = `[รายงานสอบสวนโรค] พบเคสฟันตกกระ K00.3 ระดับ ${item.severity_level} - ${item.hosp_name}`;
        
        let body = `เรียน ผู้รับผิดชอบงานระบาดวิทยาและทันตสาธารณสุขจังหวัด

เรื่อง: รายงานการสอบสวนโรคผู้ป่วยฟันตกกระ (Fluorosis - ICD10 K00.3)

จากการลงพื้นที่สอบสวนโรคโดย ${item.investigator_name || '-'} เมื่อวันที่ ${item.investigation_date} มีข้อมูลการเกิดโรคดังนี้:
- สถานบริการ: ${item.hosp_name} (รหัส 5 หลัก: ${item.hospcode})
- ข้อมูลผู้ป่วย: เพศ ${item.patient_gender || '-'}, อายุ ${item.patient_age || '0'} ปี
- ผลการตรวจ (Dean's Index): ${item.severity_level}
- ข้อมูลแหล่งน้ำความเสี่ยง: ดื่มน้ำจาก ${item.drinking_water_source || '-'} (ระยะเวลาบริโภค ${item.exposure_years || '0'} ปี)
- รายละเอียดเพิ่มเติม: ${item.details || '-'}

ติดต่อผู้รายงานสอบสวนโรค: โทร ${item.investigator_phone || '-'}
-----------------
ส่งต่อข้อมูลจากระบบ E-Fluoride Pro: http://localhost:5000/`;

        let mailtoUrl = `mailto:${projectEmail}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
        $('#btnSendInvestigationEmail').attr('href', mailtoUrl);

        // Open Modal
        let detailModal = new bootstrap.Modal(document.getElementById('investigationDetailModal'));
        detailModal.show();
    });    // ----------------------------------------------------
    // 8. AI Spatial Predictive Modeling
    // ----------------------------------------------------
    let aiMap = null;
    let aiMarkersGroup = null;
    let aiChoroplethLayer = null;
    let aiScatterChartInstance = null;
    let aiMoranScatterChartInstance = null;
    let currentAIPredictions = [];
    let aiMapMode = 'risk';
    let currentAlpha = 0;
    let currentBeta = 0;
    let currentGamma = 0;

    // Map layer mode change listener
    $(document).on('change', 'input[name="aiMapMode"]', function() {
        aiMapMode = $(this).val();
        if (currentAIPredictions && currentAIPredictions.length > 0) {
            updateAIMap(currentAIPredictions);
        }
    });

    function updateSandboxPrediction() {
        let fVal = parseFloat($('#sandbox-fluoride').val()) || 0;
        let sVal = parseFloat($('#sandbox-severe').val()) || 0;
        
        $('#sandbox-fluoride-val').text(fVal.toFixed(2));
        $('#sandbox-severe-val').text((sVal * 100).toFixed(0) + '%');
        
        let pred = currentAlpha + (currentBeta * fVal) + (currentGamma * sVal);
        pred = Math.max(0.0, Math.min(100.0, pred));
        
        $('#sandbox-result-pct').text(pred.toFixed(1) + '%');
        
        let badge = $('#sandbox-result-badge');
        let gauge = $('#sandbox-gauge');
        let badgeClass = 'bg-success';
        let badgeText = 'ปกติ (Low Risk)';
        let color = '#10b981';
        
        if (pred > 15.0) {
            badgeClass = 'bg-danger';
            badgeText = 'วิกฤต (High Risk)';
            color = '#ef4444';
        } else if (pred > 5.0) {
            badgeClass = 'bg-warning text-dark';
            badgeText = 'เฝ้าระวัง (Medium Risk)';
            color = '#f97316';
        }
        
        badge.attr('class', 'badge ' + badgeClass + ' px-3 py-2');
        badge.text(badgeText);
        
        let deg = (pred / 100) * 360;
        gauge.css('background', 'conic-gradient(' + color + ' 0deg ' + deg + 'deg, #e2e8f0 ' + deg + 'deg 360deg)');
    }

    $(document).on('input', '#sandbox-fluoride, #sandbox-severe', function() {
        updateSandboxPrediction();
    });

    function updateAILegend() {
        let legend = document.getElementById('aiMapLegend');
        if (!legend) return;
        
        let html = '';
        if (aiMapMode === 'risk') {
            html = `
                <div class="fw-bold mb-1"><i class="fas fa-exclamation-circle me-1"></i> ระดับความเสี่ยงฟันตกกระทำนาย</div>
                <div class="d-flex align-items-center mb-1"><span class="sonar-legend-dot water-alert me-2" style="background-color: #ef4444;"></span> ความเสี่ยงสูง (High Risk &gt; 15%)</div>
                <div class="d-flex align-items-center mb-1"><span class="sonar-legend-dot me-2" style="background-color: #f97316;"></span> ความเสี่ยงปานกลาง (Medium Risk 5% - 15%)</div>
                <div class="d-flex align-items-center"><span class="sonar-legend-dot me-2" style="background-color: #10b981;"></span> ความเสี่ยงต่ำ (Low Risk &lt; 5%)</div>
            `;
        } else if (aiMapMode === 'lisa_cluster') {
            html = `
                <div class="fw-bold mb-1"><i class="fas fa-th-large me-1"></i> กลุ่มความสัมพันธ์เชิงพื้นที่ LISA (p &lt; 0.05)</div>
                <div class="d-flex align-items-center mb-1"><span class="sonar-legend-dot me-2" style="background-color: #ef4444;"></span> High-High (Hotspot)</div>
                <div class="d-flex align-items-center mb-1"><span class="sonar-legend-dot me-2" style="background-color: #2563eb;"></span> Low-Low (Coldspot)</div>
                <div class="d-flex align-items-center mb-1"><span class="sonar-legend-dot me-2" style="background-color: #ec4899;"></span> High-Low (Outlier)</div>
                <div class="d-flex align-items-center mb-1"><span class="sonar-legend-dot me-2" style="background-color: #06b6d4;"></span> Low-High (Outlier)</div>
                <div class="d-flex align-items-center"><span class="sonar-legend-dot me-2" style="background-color: #94a3b8;"></span> ไม่มีนัยสำคัญ (Not Significant)</div>
            `;
        } else if (aiMapMode === 'lisa_significance') {
            html = `
                <div class="fw-bold mb-1"><i class="fas fa-star me-1"></i> ระดับนัยสำคัญ LISA Significance</div>
                <div class="d-flex align-items-center mb-1"><span class="sonar-legend-dot me-2" style="background-color: #065f46;"></span> นัยสำคัญสูงมาก (p &lt; 0.01)</div>
                <div class="d-flex align-items-center mb-1"><span class="sonar-legend-dot me-2" style="background-color: #10b981;"></span> มีนัยสำคัญ (p &lt; 0.05)</div>
                <div class="d-flex align-items-center"><span class="sonar-legend-dot me-2" style="background-color: #94a3b8;"></span> ไม่มีนัยสำคัญ (p &ge; 0.05)</div>
            `;
        }
        legend.innerHTML = html;
    }

    function loadAIPredictions() {
        showLoading();
        let filters = { 
            'ปี': $('#filter-year').val(), 
            'ภาค': $('#filter-region').val(), 
            'เขตสุขภาพ': $('#filter-zone').val(), 
            'จังหวัด': $('#filter-province').val(), 
            'อำเภอ': $('#filter-district').val(), 
            'ตำบล': $('#filter-subdistrict').val() 
        };
        fetch('/api/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(filters)
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                // Update equations & coefficients text
                $('#aiModelEquation').text(data.model.equation);
                $('#aiModelCoefficients').text(`ค่าน้ำหนักสัมประสิทธิ์ทางสถิติ: Intercept (α) = ${data.model.alpha}, ปริมาณฟลูออไรด์ (β) = ${data.model.beta}, สัดส่วนผู้ป่วยรุนแรง (γ) = ${data.model.gamma}`);

                // Update Diagram Coefficients nodes
                $('#val-coef-alpha').text(`α = ${parseFloat(data.model.alpha).toFixed(4)}`);
                $('#val-coef-beta').text(`β = ${parseFloat(data.model.beta).toFixed(4)}`);
                $('#val-coef-gamma').text(`γ = ${parseFloat(data.model.gamma).toFixed(4)}`);

                // Save coefficients globally
                currentAlpha = parseFloat(data.model.alpha) || 0;
                currentBeta = parseFloat(data.model.beta) || 0;
                currentGamma = parseFloat(data.model.gamma) || 0;

                // Update sandbox values
                updateSandboxPrediction();

                // Save predictions globally
                currentAIPredictions = data.predictions;

                // Update Table
                let rowsHtml = '';
                let allX = [];
                let allY = [];
                let lowPoints = [];
                let medPoints = [];
                let highPoints = [];

                data.predictions.forEach(p => {
                    let riskBadge = '';
                    let riskText = '';
                    if (p.predicted_risk_index > 15.0) {
                        riskBadge = '<span class="badge bg-danger">วิกฤต (High Risk)</span>';
                        riskText = 'วิกฤต (High Risk)';
                    } else if (p.predicted_risk_index > 5.0) {
                        riskBadge = '<span class="badge bg-warning text-dark">เฝ้าระวัง (Medium Risk)</span>';
                        riskText = 'เฝ้าระวัง (Medium Risk)';
                    } else {
                        riskBadge = '<span class="badge bg-success">ปกติ (Low Risk)</span>';
                        riskText = 'ปกติ (Low Risk)';
                    }

                    rowsHtml += `
                        <tr>
                            <td class="fw-bold ps-3">${p.province}</td>
                            <td>${p.district}</td>
                            <td class="text-center">${p.water_avg_ppm}</td>
                            <td class="text-center">${p.fluorosis_cases}</td>
                            <td class="text-center">${p.severe_cases}</td>
                            <td class="text-center fw-bold text-theme">${p.predicted_risk_index}%</td>
                            <td class="text-center">${riskBadge}</td>
                            <td class="text-center">
                                <div class="d-flex justify-content-center gap-1">
                                    <button class="btn btn-sm fly-to-btn" style="background:#f1f5f9; color:#0ea5e9; border-radius:8px;" data-lat="${p.lat}" data-lon="${p.lng}" title="แสดงบนแผนที่"><i class="fas fa-map-marker-alt"></i></button>
                                    <button class="btn btn-sm btn-primary-modern open-drawer-btn" 
                                        data-name="อ.${p.district} จ.${p.province}" 
                                        data-lat="${p.lat}" 
                                        data-lng="${p.lng}" 
                                        data-type="ai_prediction" 
                                        data-prov="${p.province}" 
                                        data-dist="${p.district}" 
                                        data-subdist="-" 
                                        data-val="${p.predicted_risk_index}" 
                                        data-status="${riskText}"
                                        data-detail="ทำนายระดับความเสี่ยง: ${riskText} (Risk Index: ${p.predicted_risk_index}%) <br>ปริมาณฟลูออไรด์เฉลี่ยในน้ำ: ${p.water_avg_ppm} ppm"
                                        data-water-ppm="${p.water_avg_ppm}"
                                        data-cases="${p.fluorosis_cases}"
                                        data-severe="${p.severe_cases}"
                                        data-lisa-i="${p.lisa_i}"
                                        data-lisa-p="${p.lisa_p}"
                                        data-lisa-quad="${p.lisa_quad}"
                                        style="border-radius:8px; padding: 4px 8px; font-size: 0.75rem;"
                                        title="ดูรายละเอียดเชิงลึก">
                                        <i class="fas fa-info-circle"></i>
                                    </button>
                                </div>
                            </td>
                        </tr>
                    `;

                    let x = parseFloat(p.water_avg_ppm);
                    let y = parseFloat(p.predicted_risk_index);
                    if (!isNaN(x) && !isNaN(y)) {
                        allX.push(x);
                        allY.push(y);
                        let pt = { x: x, y: y, district: p.district, province: p.province, lisa_i: p.lisa_i, lisa_p: p.lisa_p, lisa_quad: p.lisa_quad };
                        if (y > 15.0) {
                            highPoints.push(pt);
                        } else if (y > 5.0) {
                            medPoints.push(pt);
                        } else {
                            lowPoints.push(pt);
                        }
                    }
                });
                $('#aiPredictionTableBody').html(rowsHtml);

                // Initialize table styling if DataTable is not already initialized
                if ($.fn.DataTable.isDataTable('#aiPredictionTable')) {
                    $('#aiPredictionTable').DataTable().clear().destroy();
                }
                $('#aiPredictionTable').DataTable({
                    pageLength: 10,
                    responsive: true,
                    autoWidth: false,
                    dom: '<"d-flex justify-content-between"<"row"<"col-md-auto"l><"col-md-auto"B>>>rt<"d-flex justify-content-between"ip>',
                    buttons: [
                        { extend: 'copy', text: '<i class="fas fa-copy me-1"></i> Copy' },
                        { extend: 'csv', text: '<i class="fas fa-file-csv me-1"></i> CSV', charset: 'utf-8', bom: true },
                        { extend: 'print', text: '<i class="fas fa-print me-1"></i> Print' }
                    ]
                });

                // Calculate OLS linear regression for fluoride vs risk index
                let n = allX.length;
                let m = 0;
                let c = 0;
                if (n > 0) {
                    let sumX = 0, sumY = 0, sumXY = 0, sumXX = 0;
                    for (let i = 0; i < n; i++) {
                        sumX += allX[i];
                        sumY += allY[i];
                        sumXY += allX[i] * allY[i];
                        sumXX += allX[i] * allX[i];
                    }
                    let denom = (n * sumXX - sumX * sumX);
                    m = denom === 0 ? 0 : (n * sumXY - sumX * sumY) / denom;
                    c = (sumY - m * sumX) / n;
                }

                let trendlinePoints = [];
                if (n > 0) {
                    let minX = Math.min(...allX);
                    let maxX = Math.max(...allX);
                    let buffer = (maxX - minX) * 0.05 || 0.1;
                    let lineMinX = Math.max(0, minX - buffer);
                    let lineMaxX = maxX + buffer;
                    trendlinePoints = [
                        { x: lineMinX, y: Math.max(0, m * lineMinX + c) },
                        { x: lineMaxX, y: Math.max(0, m * lineMaxX + c) }
                    ];
                }

                // Render Chart.js Scatter Chart + Regression line
                if (aiScatterChartInstance) {
                    aiScatterChartInstance.destroy();
                }
                let ctx = document.getElementById('aiScatterChart');
                if (ctx) {
                    aiScatterChartInstance = new Chart(ctx.getContext('2d'), {
                        type: 'scatter',
                        data: {
                            datasets: [
                                {
                                    label: 'ความเสี่ยงต่ำ (< 5%)',
                                    data: lowPoints,
                                    backgroundColor: '#10b981',
                                    borderColor: '#ffffff',
                                    borderWidth: 1,
                                    pointRadius: 6,
                                    pointHoverRadius: 8
                                },
                                {
                                    label: 'ความเสี่ยงปานกลาง (5% - 15%)',
                                    data: medPoints,
                                    backgroundColor: '#f97316',
                                    borderColor: '#ffffff',
                                    borderWidth: 1,
                                    pointRadius: 6,
                                    pointHoverRadius: 8
                                },
                                {
                                    label: 'ความเสี่ยงสูง (> 15%)',
                                    data: highPoints,
                                    backgroundColor: '#ef4444',
                                    borderColor: '#ffffff',
                                    borderWidth: 1,
                                    pointRadius: 6,
                                    pointHoverRadius: 8
                                },
                                {
                                    label: 'เส้นแนวโน้มการทำนาย (OLS Trendline)',
                                    data: trendlinePoints,
                                    type: 'line',
                                    showLine: true,
                                    fill: false,
                                    borderColor: '#475569',
                                    borderDash: [5, 5],
                                    borderWidth: 2,
                                    pointRadius: 0,
                                    pointHoverRadius: 0
                                }
                            ]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    display: true,
                                    position: 'top',
                                    labels: {
                                        font: { family: 'Prompt', size: 11 }
                                    }
                                },
                                tooltip: {
                                    callbacks: {
                                        label: function(context) {
                                            if (context.datasetIndex === 3) {
                                                return `สมการแนวโน้ม: y = ${m.toFixed(4)}x + ${c.toFixed(4)}`;
                                            }
                                            let pt = context.raw;
                                            return `อ.${pt.district} จ.${pt.province}: ฟลูออไรด์ ${pt.x} ppm, เสี่ยงทำนาย ${pt.y}%`;
                                        }
                                    }
                                }
                            },
                            onClick: (e, elements) => {
                                if (elements.length > 0) {
                                    let elementIndex = elements[0].index;
                                    let datasetIndex = elements[0].datasetIndex;
                                    if (datasetIndex === 3) return; // Ignore trendline clicks
                                    let dataset = aiScatterChartInstance.data.datasets[datasetIndex];
                                    let pt = dataset.data[elementIndex];
                                    let original = data.predictions.find(p => p.district === pt.district && p.province === pt.province);
                                    if (original) {
                                        let lat = parseFloat(original.lat);
                                        let lng = parseFloat(original.lng);
                                        let riskText = 'ปกติ (Low Risk)';
                                        if (original.predicted_risk_index > 15.0) {
                                            riskText = 'วิกฤต (High Risk)';
                                        } else if (original.predicted_risk_index > 5.0) {
                                            riskText = 'เฝ้าระวัง (Medium Risk)';
                                        }
                                        let detailText = `ทำนายระดับความเสี่ยง: ${riskText} (Risk Index: ${original.predicted_risk_index}%) <br>ปริมาณฟลูออไรด์เฉลี่ยในน้ำ: ${original.water_avg_ppm} ppm`;
                                        openDetailDrawer({
                                            name: `อ.${original.district} จ.${original.province}`,
                                            type: 'ai_prediction',
                                            prov: original.province,
                                            dist: original.district,
                                            subdist: '-',
                                            val: original.predicted_risk_index,
                                            status: riskText,
                                            detail: detailText,
                                            lat: lat,
                                            lng: lng,
                                            water_ppm: original.water_avg_ppm,
                                            cases: original.fluorosis_cases,
                                            severe: original.severe_cases,
                                            lisa_i: original.lisa_i,
                                            lisa_p: original.lisa_p,
                                            lisa_quad: original.lisa_quad
                                        });
                                    }
                                }
                            },
                            scales: {
                                x: {
                                    title: {
                                        display: true,
                                        text: 'ปริมาณฟลูออไรด์เฉลี่ยในน้ำดื่ม (ppm)',
                                        font: { family: 'Prompt', size: 12, weight: 'bold' }
                                    },
                                    ticks: { font: { family: 'Outfit', size: 11 } }
                                },
                                y: {
                                    title: {
                                        display: true,
                                        text: 'ดัชนีความเสี่ยงทำนาย (%)',
                                        font: { family: 'Prompt', size: 12, weight: 'bold' }
                                    },
                                    ticks: { font: { family: 'Outfit', size: 11 } },
                                    beginAtZero: true
                                }
                            }
                        }
                    });
                }

                // Render Chart.js Moran Scatter Plot
                let moranHH = [];
                let moranLH = [];
                let moranLL = [];
                let moranHL = [];
                let zScores = [];

                data.predictions.forEach(p => {
                    let pt = { x: p.z_score, y: p.z_lag, district: p.district, province: p.province, i: p.lisa_i, p: p.lisa_p };
                    zScores.push(p.z_score);
                    if (p.lisa_quad === 1) moranHH.push(pt);
                    else if (p.lisa_quad === 2) moranLH.push(pt);
                    else if (p.lisa_quad === 3) moranLL.push(pt);
                    else if (p.lisa_quad === 4) moranHL.push(pt);
                });

                let minZ = Math.min(...zScores);
                let maxZ = Math.max(...zScores);
                let lineMinZ = minZ * 1.1;
                let lineMaxZ = maxZ * 1.1;
                let gI = data.model.global_moran_i;

                let moranTrendline = [
                    { x: lineMinZ, y: gI * lineMinZ },
                    { x: lineMaxZ, y: gI * lineMaxZ }
                ];

                if (aiMoranScatterChartInstance) {
                    aiMoranScatterChartInstance.destroy();
                }

                let mCtx = document.getElementById('aiMoranScatterChart');
                if (mCtx) {
                    aiMoranScatterChartInstance = new Chart(mCtx.getContext('2d'), {
                        type: 'scatter',
                        data: {
                            datasets: [
                                {
                                    label: 'High-High (HH)',
                                    data: moranHH,
                                    backgroundColor: '#ef4444',
                                    borderColor: '#ffffff',
                                    borderWidth: 1,
                                    pointRadius: 5,
                                    pointHoverRadius: 7
                                },
                                {
                                    label: 'Low-High (LH)',
                                    data: moranLH,
                                    backgroundColor: '#06b6d4',
                                    borderColor: '#ffffff',
                                    borderWidth: 1,
                                    pointRadius: 5,
                                    pointHoverRadius: 7
                                },
                                {
                                    label: 'Low-Low (LL)',
                                    data: moranLL,
                                    backgroundColor: '#2563eb',
                                    borderColor: '#ffffff',
                                    borderWidth: 1,
                                    pointRadius: 5,
                                    pointHoverRadius: 7
                                },
                                {
                                    label: 'High-Low (HL)',
                                    data: moranHL,
                                    backgroundColor: '#ec4899',
                                    borderColor: '#ffffff',
                                    borderWidth: 1,
                                    pointRadius: 5,
                                    pointHoverRadius: 7
                                },
                                {
                                    label: `เส้น Moran's I (${gI.toFixed(4)})`,
                                    data: moranTrendline,
                                    type: 'line',
                                    showLine: true,
                                    fill: false,
                                    borderColor: '#0f172a',
                                    borderWidth: 2,
                                    pointRadius: 0,
                                    pointHoverRadius: 0
                                }
                            ]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    display: true,
                                    position: 'top',
                                    labels: { font: { family: 'Prompt', size: 9 } }
                                },
                                tooltip: {
                                    callbacks: {
                                        label: function(context) {
                                            if (context.datasetIndex === 4) {
                                                return `Global Moran's I = ${gI.toFixed(4)}`;
                                            }
                                            let pt = context.raw;
                                            return `อ.${pt.district} จ.${pt.province}: z = ${pt.x.toFixed(2)}, Lag = ${pt.y.toFixed(2)} (Local I = ${pt.i.toFixed(2)}, p = ${pt.p.toFixed(3)})`;
                                        }
                                    }
                                }
                            },
                            scales: {
                                x: {
                                    title: {
                                        display: true,
                                        text: 'ค่ามาตรฐาน z-Score (เสี่ยงทำนาย)',
                                        font: { family: 'Prompt', size: 10, weight: 'bold' }
                                    },
                                    ticks: { font: { family: 'Outfit', size: 10 } }
                                },
                                y: {
                                    title: {
                                        display: true,
                                        text: 'ค่าเฉลี่ยเพื่อนบ้าน Spatial Lag (Wz)',
                                        font: { family: 'Prompt', size: 10, weight: 'bold' }
                                    },
                                    ticks: { font: { family: 'Outfit', size: 10 } }
                                }
                            }
                        }
                    });
                }

                // Update Map
                updateAIMap(data.predictions);
                
                if (data.dropdowns) {
                    function updateSelect(id, options, currentValue) { 
                        let select = $(id); 
                        select.empty(); 
                        let currStr = String(currentValue); 
                        options.forEach(opt => { 
                            let isSelected = (String(opt) === currStr) ? 'selected' : ''; 
                            select.append(`<option value="${opt}" ${isSelected}>${opt === 'ทั้งหมด' ? '-- ทั้งหมด --' : opt}</option>`); 
                        }); 
                    }
                    updateSelect('#filter-year', data.dropdowns.years, $('#filter-year').val());
                    updateSelect('#filter-region', data.dropdowns.regions, $('#filter-region').val());
                    updateSelect('#filter-zone', data.dropdowns.zones, $('#filter-zone').val());
                    updateSelect('#filter-province', data.dropdowns.provinces, $('#filter-province').val());
                    updateSelect('#filter-district', data.dropdowns.districts, $('#filter-district').val());
                    updateSelect('#filter-subdistrict', data.dropdowns.subdistricts, $('#filter-subdistrict').val());
                    let p = $('#filter-province').val(); 
                    let d = $('#filter-district').val();
                    $('#filter-district').prop('disabled', p === 'ทั้งหมด'); 
                    $('#filter-subdistrict').prop('disabled', p === 'ทั้งหมด' || d === 'ทั้งหมด');
                }
            } else {
                alert('เกิดข้อผิดพลาดในการคำนวณโมเดล AI: ' + data.message);
            }
        })
        .catch(err => {
            console.error('Error fetching AI predictions:', err);
            alert('ไม่สามารถเชื่อมต่อระบบ AI ได้: ' + err.message);
        })
        .finally(() => hideLoading());
    }

    function getAIFeatureStyle(feature, predictions) {
        let ampName = getAmpName(feature.properties);
        let provName = getProvName(feature.properties);
        let p = predictions.find(pred => cleanName(pred.district) === ampName && cleanName(pred.province) === provName);
        
        let fillColor = '#cbd5e1';
        let fillOpacity = 0.1;
        let weight = 1.0;
        let color = '#94a3b8'; // border
        
        if (p) {
            fillOpacity = 0.55;
            weight = 1.2;
            color = '#ffffff';
            
            if (aiMapMode === 'risk') {
                if (p.predicted_risk_index > 15.0) {
                    fillColor = '#ef4444';
                } else if (p.predicted_risk_index > 5.0) {
                    fillColor = '#f97316';
                } else {
                    fillColor = '#10b981';
                }
            } else if (aiMapMode === 'lisa_cluster') {
                if (p.lisa_p < 0.05) {
                    if (p.lisa_quad === 1) fillColor = '#ef4444'; // HH
                    else if (p.lisa_quad === 2) fillColor = '#06b6d4'; // LH
                    else if (p.lisa_quad === 3) fillColor = '#2563eb'; // LL
                    else if (p.lisa_quad === 4) fillColor = '#ec4899'; // HL
                } else {
                    fillColor = '#cbd5e1'; // NS
                    fillOpacity = 0.25;
                    color = '#e2e8f0';
                }
            } else if (aiMapMode === 'lisa_significance') {
                if (p.lisa_p < 0.01) {
                    fillColor = '#065f46';
                } else if (p.lisa_p < 0.05) {
                    fillColor = '#10b981';
                } else {
                    fillColor = '#cbd5e1';
                    fillOpacity = 0.25;
                    color = '#e2e8f0';
                }
            }
        }
        
        return {
            fillColor: fillColor,
            fillOpacity: fillOpacity,
            weight: weight,
            opacity: 1,
            color: color
        };
    }

    function onEachAIFeature(feature, layer, predictions) {
        let ampName = getAmpName(feature.properties);
        let provName = getProvName(feature.properties);
        let p = predictions.find(pred => cleanName(pred.district) === ampName && cleanName(pred.province) === provName);
        
        if (p) {
            let styleColor = '#cbd5e1';
            let riskType = 'ปกติ (Low Risk)';
            let badgeStyle = 'background-color: #10b981; color: white;';
            
            if (aiMapMode === 'risk') {
                if (p.predicted_risk_index > 15.0) {
                    riskType = 'วิกฤต (High Risk)';
                    badgeStyle = 'background-color: #ef4444; color: white;';
                } else if (p.predicted_risk_index > 5.0) {
                    riskType = 'เฝ้าระวัง (Medium Risk)';
                    badgeStyle = 'background-color: #f97316; color: white;';
                } else {
                    riskType = 'ปกติ (Low Risk)';
                    badgeStyle = 'background-color: #10b981; color: white;';
                }
            } else if (aiMapMode === 'lisa_cluster') {
                if (p.lisa_p < 0.05) {
                    if (p.lisa_quad === 1) {
                        riskType = 'High-High (Hotspot)';
                        badgeStyle = 'background-color: #ef4444; color: white;';
                    } else if (p.lisa_quad === 2) {
                        riskType = 'Low-High Outlier';
                        badgeStyle = 'background-color: #06b6d4; color: white;';
                    } else if (p.lisa_quad === 3) {
                        riskType = 'Low-Low (Coldspot)';
                        badgeStyle = 'background-color: #2563eb; color: white;';
                    } else if (p.lisa_quad === 4) {
                        riskType = 'High-Low Outlier';
                        badgeStyle = 'background-color: #ec4899; color: white;';
                    }
                } else {
                    riskType = 'ไม่มีนัยสำคัญ (Not Significant)';
                    badgeStyle = 'background-color: #cbd5e1; color: #475569; border: 1px solid #94a3b8;';
                }
            } else if (aiMapMode === 'lisa_significance') {
                if (p.lisa_p < 0.01) {
                    riskType = 'นัยสำคัญสูงมาก (p < 0.01)';
                    badgeStyle = 'background-color: #065f46; color: white;';
                } else if (p.lisa_p < 0.05) {
                    riskType = 'มีนัยสำคัญ (p < 0.05)';
                    badgeStyle = 'background-color: #10b981; color: white;';
                } else {
                    riskType = 'ไม่มีนัยสำคัญ (p >= 0.05)';
                    badgeStyle = 'background-color: #cbd5e1; color: #475569; border: 1px solid #94a3b8;';
                }
            }
            
            let lisaText = '';
            if (p.lisa_p < 0.05) {
                if (p.lisa_quad === 1) lisaText = 'High-High (Hotspot)';
                else if (p.lisa_quad === 2) lisaText = 'Low-High Outlier';
                else if (p.lisa_quad === 3) lisaText = 'Low-Low (Coldspot)';
                else if (p.lisa_quad === 4) lisaText = 'High-Low Outlier';
            } else {
                lisaText = 'ไม่มีนัยสำคัญ (Not Significant)';
            }
            
            let popupHtml = `
                <div style="font-family:'Prompt', sans-serif; min-width: 180px;">
                    <b style="font-size: 0.95rem; color:#0f172a;">อ.${p.district} จ.${p.province}</b>
                    <hr style="margin: 8px 0; border-color: #e2e8f0;">
                    <div class="mb-2"><span class="badge" style="font-size:0.7rem; ${badgeStyle}">${riskType}</span></div>
                    <div class="small text-muted mb-1"><b>ฟลูออไรด์เฉลี่ย:</b> ${p.water_avg_ppm} ppm</div>
                    <div class="small text-muted mb-1"><b>ดัชนีเสี่ยงทำนาย:</b> ${p.predicted_risk_index}%</div>
                    <div class="small text-muted mb-1"><b>กลุ่ม LISA:</b> ${lisaText}</div>
                    <div class="small text-muted mb-2"><b>Local Moran's I:</b> ${p.lisa_i} (p = ${p.lisa_p})</div>
                    <button class="btn btn-sm btn-primary-modern w-100 open-drawer-btn" 
                        data-name="อ.${p.district} จ.${p.province}" 
                        data-lat="${p.lat}" 
                        data-lng="${p.lng}" 
                        data-type="ai_prediction" 
                        data-prov="${p.province}" 
                        data-dist="${p.district}" 
                        data-subdist="-" 
                        data-val="${p.predicted_risk_index}" 
                        data-status="${riskType}"
                        data-detail="ทำนายระดับความเสี่ยง: ${p.predicted_risk_index}% <br>กลุ่ม LISA: ${lisaText}"
                        data-water-ppm="${p.water_avg_ppm}"
                        data-cases="${p.fluorosis_cases}"
                        data-severe="${p.severe_cases}"
                        data-lisa-i="${p.lisa_i}"
                        data-lisa-p="${p.lisa_p}"
                        data-lisa-quad="${p.lisa_quad}"
                        style="font-size: 0.72rem; border-radius: 6px; padding: 4px 8px;">
                        ดูรายละเอียดเชิงลึก <i class="fas fa-arrow-right ms-1"></i>
                    </button>
                </div>
            `;
            layer.bindPopup(popupHtml);
            layer.on({
                mouseover: function(e) {
                    e.target.setStyle({ weight: 2.5, color: '#334155', fillOpacity: 0.8 });
                    e.target.bringToFront();
                },
                mouseout: function(e) {
                    if (aiChoroplethLayer) {
                        aiChoroplethLayer.resetStyle(e.target);
                    }
                }
            });
        }
    }

    function renderAIGeoJson(geojson, predictions) {
        if (aiChoroplethLayer) {
            aiMap.removeLayer(aiChoroplethLayer);
        }
        
        aiChoroplethLayer = L.geoJSON(geojson, {
            style: function(f) { return getAIFeatureStyle(f, predictions); },
            onEachFeature: function(f, l) { onEachAIFeature(f, l, predictions); }
        }).addTo(aiMap);
        
        aiMarkersGroup.clearLayers();
        let bounds = [];
        
        predictions.forEach(p => {
            let lat = parseFloat(p.lat);
            let lng = parseFloat(p.lng);
            if (!isNaN(lat) && !isNaN(lng) && lat !== 0 && lng !== 0) {
                bounds.push([lat, lng]);
                let styleColor = '#10b981';
                let riskType = 'ปกติ (Low Risk)';
                let badgeStyle = 'background-color: #10b981; color: white;';
                
                if (aiMapMode === 'risk') {
                    if (p.predicted_risk_index > 15.0) {
                        styleColor = '#ef4444';
                        riskType = 'วิกฤต (High Risk)';
                        badgeStyle = 'background-color: #ef4444; color: white;';
                    } else if (p.predicted_risk_index > 5.0) {
                        styleColor = '#f97316';
                        riskType = 'เฝ้าระวัง (Medium Risk)';
                        badgeStyle = 'background-color: #f97316; color: white;';
                    } else {
                        styleColor = '#10b981';
                        riskType = 'ปกติ (Low Risk)';
                        badgeStyle = 'background-color: #10b981; color: white;';
                    }
                } else if (aiMapMode === 'lisa_cluster') {
                    if (p.lisa_p < 0.05) {
                        if (p.lisa_quad === 1) {
                            styleColor = '#ef4444';
                            riskType = 'High-High (Hotspot)';
                            badgeStyle = 'background-color: #ef4444; color: white;';
                        } else if (p.lisa_quad === 2) {
                            styleColor = '#06b6d4';
                            riskType = 'Low-High Outlier';
                            badgeStyle = 'background-color: #06b6d4; color: white;';
                        } else if (p.lisa_quad === 3) {
                            styleColor = '#2563eb';
                            riskType = 'Low-Low (Coldspot)';
                            badgeStyle = 'background-color: #2563eb; color: white;';
                        } else if (p.lisa_quad === 4) {
                            styleColor = '#ec4899';
                            riskType = 'High-Low Outlier';
                            badgeStyle = 'background-color: #ec4899; color: white;';
                        }
                    } else {
                        styleColor = '#94a3b8';
                        riskType = 'ไม่มีนัยสำคัญ (Not Significant)';
                        badgeStyle = 'background-color: #cbd5e1; color: #475569; border: 1px solid #94a3b8;';
                    }
                } else if (aiMapMode === 'lisa_significance') {
                    if (p.lisa_p < 0.01) {
                        styleColor = '#065f46';
                        riskType = 'นัยสำคัญสูงมาก (p < 0.01)';
                        badgeStyle = 'background-color: #065f46; color: white;';
                    } else if (p.lisa_p < 0.05) {
                        styleColor = '#10b981';
                        riskType = 'มีนัยสำคัญ (p < 0.05)';
                        badgeStyle = 'background-color: #10b981; color: white;';
                    } else {
                        styleColor = '#94a3b8';
                        riskType = 'ไม่มีนัยสำคัญ (p >= 0.05)';
                        badgeStyle = 'background-color: #cbd5e1; color: #475569; border: 1px solid #94a3b8;';
                    }
                }

                let iconHtml = `
                    <div class="alert-sonar-marker no-default-ripple" style="background-color: ${styleColor}; border-color: white;">
                        <i class="fas fa-brain"></i>
                        <div style="
                            position: absolute;
                            top: -2px; left: -2px;
                            width: 20px; height: 20px;
                            border-radius: 50%;
                            border: 2px solid ${styleColor};
                            animation: sonar-ripple 1.8s infinite ease-out;
                            pointer-events: none;
                        "></div>
                    </div>
                `;

                let customIcon = L.divIcon({
                    className: '',
                    html: iconHtml,
                    iconSize: [20, 20],
                    iconAnchor: [10, 10]
                });

                let detailText = `ทำนายระดับความเสี่ยง: ${p.predicted_risk_index}% <br>กลุ่ม LISA: ${p.lisa_quad === 1 ? 'High-High' : p.lisa_quad === 3 ? 'Low-Low' : p.lisa_quad === 4 ? 'High-Low' : 'Low-High'} (p = ${p.lisa_p})`;

                let popupHtml = `
                    <div class="p-1" style="font-family:'Prompt', sans-serif; min-width: 180px;">
                        <h6 class="fw-bold m-0 text-slate-800" style="font-size: 0.9rem;">อ.${p.district} จ.${p.province}</h6>
                        <span class="badge mb-2 mt-1" style="font-size:0.7rem; ${badgeStyle}">${riskType}</span>
                        <div class="small text-muted mb-1"><b>ฟลูออไรด์เฉลี่ย:</b> ${p.water_avg_ppm} ppm</div>
                        <div class="small text-muted mb-1"><b>ดัชนีทำนายความเสี่ยง:</b> ${p.predicted_risk_index}%</div>
                        <div class="small text-muted mb-1"><b>Local Moran's I:</b> ${p.lisa_i} (p = ${p.lisa_p})</div>
                        <button class="btn btn-sm btn-primary-modern w-100 mt-2 px-2 py-1 open-drawer-btn" 
                            data-name="อ.${p.district} จ.${p.province}" 
                            data-lat="${lat}" 
                            data-lng="${lng}" 
                            data-type="ai_prediction" 
                            data-prov="${p.province}" 
                            data-dist="${p.district}" 
                            data-subdist="-" 
                            data-val="${p.predicted_risk_index}" 
                            data-status="${riskType}"
                            data-detail="${detailText}"
                            data-water-ppm="${p.water_avg_ppm}"
                            data-cases="${p.fluorosis_cases}"
                            data-severe="${p.severe_cases}"
                            data-lisa-i="${p.lisa_i}"
                            data-lisa-p="${p.lisa_p}"
                            data-lisa-quad="${p.lisa_quad}"
                            style="font-size: 0.75rem; border-radius: 8px;">
                            ดูข้อมูลเชิงลึก <i class="fas fa-arrow-right ms-1"></i>
                        </button>
                    </div>
                `;

                let marker = L.marker([lat, lng], { icon: customIcon }).bindPopup(popupHtml);
                aiMarkersGroup.addLayer(marker);
            }
        });

        if (bounds.length > 0) {
            aiMap.flyToBounds(bounds, { padding: [30, 30] });
        } else {
            aiMap.flyTo([13.0, 101.5], 6);
        }
    }

    function renderAIMarkersOnly(predictions) {
        if (aiChoroplethLayer) {
            aiMap.removeLayer(aiChoroplethLayer);
            aiChoroplethLayer = null;
        }
        aiMarkersGroup.clearLayers();
        let bounds = [];
        
        predictions.forEach(p => {
            let lat = parseFloat(p.lat);
            let lng = parseFloat(p.lng);
            if (!isNaN(lat) && !isNaN(lng) && lat !== 0 && lng !== 0) {
                bounds.push([lat, lng]);
                let styleColor = '#10b981';
                let riskType = 'ปกติ (Low Risk)';
                let badgeStyle = 'background-color: #10b981; color: white;';
                
                if (aiMapMode === 'risk') {
                    if (p.predicted_risk_index > 15.0) {
                        styleColor = '#ef4444';
                        riskType = 'วิกฤต (High Risk)';
                        badgeStyle = 'background-color: #ef4444; color: white;';
                    } else if (p.predicted_risk_index > 5.0) {
                        styleColor = '#f97316';
                        riskType = 'เฝ้าระวัง (Medium Risk)';
                        badgeStyle = 'background-color: #f97316; color: white;';
                    } else {
                        styleColor = '#10b981';
                        riskType = 'ปกติ (Low Risk)';
                        badgeStyle = 'background-color: #10b981; color: white;';
                    }
                } else if (aiMapMode === 'lisa_cluster') {
                    if (p.lisa_p < 0.05) {
                        if (p.lisa_quad === 1) {
                            styleColor = '#ef4444';
                            riskType = 'High-High (Hotspot)';
                            badgeStyle = 'background-color: #ef4444; color: white;';
                        } else if (p.lisa_quad === 2) {
                            styleColor = '#06b6d4';
                            riskType = 'Low-High Outlier';
                            badgeStyle = 'background-color: #06b6d4; color: white;';
                        } else if (p.lisa_quad === 3) {
                            styleColor = '#2563eb';
                            riskType = 'Low-Low (Coldspot)';
                            badgeStyle = 'background-color: #2563eb; color: white;';
                        } else if (p.lisa_quad === 4) {
                            styleColor = '#ec4899';
                            riskType = 'High-Low Outlier';
                            badgeStyle = 'background-color: #ec4899; color: white;';
                        }
                    } else {
                        styleColor = '#94a3b8';
                        riskType = 'ไม่มีนัยสำคัญ (Not Significant)';
                        badgeStyle = 'background-color: #cbd5e1; color: #475569; border: 1px solid #94a3b8;';
                    }
                } else if (aiMapMode === 'lisa_significance') {
                    if (p.lisa_p < 0.01) {
                        styleColor = '#065f46';
                        riskType = 'นัยสำคัญสูงมาก (p < 0.01)';
                        badgeStyle = 'background-color: #065f46; color: white;';
                    } else if (p.lisa_p < 0.05) {
                        styleColor = '#10b981';
                        riskType = 'มีนัยสำคัญ (p < 0.05)';
                        badgeStyle = 'background-color: #10b981; color: white;';
                    } else {
                        styleColor = '#94a3b8';
                        riskType = 'ไม่มีนัยสำคัญ (p >= 0.05)';
                        badgeStyle = 'background-color: #cbd5e1; color: #475569; border: 1px solid #94a3b8;';
                    }
                }

                let iconHtml = `
                    <div class="alert-sonar-marker no-default-ripple" style="background-color: ${styleColor}; border-color: white;">
                        <i class="fas fa-brain"></i>
                        <div style="
                            position: absolute;
                            top: -2px; left: -2px;
                            width: 20px; height: 20px;
                            border-radius: 50%;
                            border: 2px solid ${styleColor};
                            animation: sonar-ripple 1.8s infinite ease-out;
                            pointer-events: none;
                        "></div>
                    </div>
                `;

                let customIcon = L.divIcon({
                    className: '',
                    html: iconHtml,
                    iconSize: [20, 20],
                    iconAnchor: [10, 10]
                });

                let detailText = `ทำนายระดับความเสี่ยง: ${p.predicted_risk_index}% <br>กลุ่ม LISA: ${p.lisa_quad === 1 ? 'High-High' : p.lisa_quad === 3 ? 'Low-Low' : p.lisa_quad === 4 ? 'High-Low' : 'Low-High'} (p = ${p.lisa_p})`;

                let popupHtml = `
                    <div class="p-1" style="font-family:'Prompt', sans-serif; min-width: 180px;">
                        <h6 class="fw-bold m-0 text-slate-800" style="font-size: 0.9rem;">อ.${p.district} จ.${p.province}</h6>
                        <span class="badge mb-2 mt-1" style="font-size:0.7rem; ${badgeStyle}">${riskType}</span>
                        <div class="small text-muted mb-1"><b>ฟลูออไรด์เฉลี่ย:</b> ${p.water_avg_ppm} ppm</div>
                        <div class="small text-muted mb-1"><b>ดัชนีทำนายความเสี่ยง:</b> ${p.predicted_risk_index}%</div>
                        <div class="small text-muted mb-1"><b>Local Moran's I:</b> ${p.lisa_i} (p = ${p.lisa_p})</div>
                        <button class="btn btn-sm btn-primary-modern w-100 mt-2 px-2 py-1 open-drawer-btn" 
                            data-name="อ.${p.district} จ.${p.province}" 
                            data-lat="${lat}" 
                            data-lng="${lng}" 
                            data-type="ai_prediction" 
                            data-prov="${p.province}" 
                            data-dist="${p.district}" 
                            data-subdist="-" 
                            data-val="${p.predicted_risk_index}" 
                            data-status="${riskType}"
                            data-detail="${detailText}"
                            data-water-ppm="${p.water_avg_ppm}"
                            data-cases="${p.fluorosis_cases}"
                            data-severe="${p.severe_cases}"
                            data-lisa-i="${p.lisa_i}"
                            data-lisa-p="${p.lisa_p}"
                            data-lisa-quad="${p.lisa_quad}"
                            style="font-size: 0.75rem; border-radius: 8px;">
                            ดูข้อมูลเชิงลึก <i class="fas fa-arrow-right ms-1"></i>
                        </button>
                    </div>
                `;

                let marker = L.marker([lat, lng], { icon: customIcon }).bindPopup(popupHtml);
                aiMarkersGroup.addLayer(marker);
            }
        });

        if (bounds.length > 0) {
            aiMap.flyToBounds(bounds, { padding: [30, 30] });
        } else {
            aiMap.flyTo([13.0, 101.5], 6);
        }
    }

    function updateAIMap(predictions) {
        let aiMapContainer = document.getElementById('aiMap');
        if (!aiMapContainer) return;

        if (!aiMap) {
            aiMap = L.map('aiMap', { maxBounds: [[5.0, 97.0], [21.0, 106.0]], maxBoundsViscosity: 1.0, minZoom: 5 }).setView([15.0, 100.0], 6);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                crossOrigin: true,
                attribution: '&copy; OpenStreetMap contributors'
            }).addTo(aiMap);
            aiMarkersGroup = L.markerClusterGroup({ disableClusteringAtZoom: 12 });
            aiMap.addLayer(aiMarkersGroup);
        }

        // Update current map mode legend
        updateAILegend();

        // Load districts geojson boundaries for choropleth mapping
        let geojsonUrl = '/static/districts.geojson';
        if (geoJsonCache[geojsonUrl]) {
            renderAIGeoJson(geoJsonCache[geojsonUrl], predictions);
        } else {
            fetch(geojsonUrl)
                .then(res => res.json())
                .then(data => {
                    geoJsonCache[geojsonUrl] = data;
                    renderAIGeoJson(data, predictions);
                })
                .catch(err => {
                    console.error('Error loading districts GeoJSON for AI Map:', err);
                    renderAIMarkersOnly(predictions);
                });
        }
        
        // Force refresh layout size
        setTimeout(() => {
            aiMap.invalidateSize();
        }, 300);
    }

    // Initial load
    fetchSchemas().then(() => {
        fetch('/static/provinces.geojson').catch(() => console.log("Loading Map GeoJSON..."));
        logVisit(currentType, 'VIEW');
        loadData();
    });
});


// ==========================================
// NEW FEATURE LOGIC (Registration, Child Cases, RBAC)
// ==========================================

function updateMenuVisibility() {
    let role = sessionStorage.getItem('userRole');
    if(role) {
        $('#menuChildCases').show();
        if(role === 'admin') {
            $('#menuAdminUsers').show();
        } else {
            $('#menuAdminUsers').hide();
        }
    } else {
        $('#menuChildCases').hide();
        $('#menuAdminUsers').hide();
    }
}

$(document).ready(function() {
    // Menu Clicks
    $('#menuChildCases').click(function(e) {
        e.preventDefault();
        $('.view-section').hide();
        $('.nav-link').removeClass('active');
        $(this).addClass('active');
        $('#childCasesView').fadeIn();
    });
    
    $('#menuAdminUsers').click(function(e) {
        e.preventDefault();
        $('.view-section').hide();
        $('.nav-link').removeClass('active');
        $(this).addClass('active');
        $('#adminUsersView').fadeIn();
        loadAdminUsers();
    });
    
    // Register UI
    $('#linkToRegister').click(function(e) {
        e.preventDefault();
        $('#loginModal').modal('hide');
        $('#registerModal').modal('show');
    });
    
    $('#registerForm').submit(function(e) {
        e.preventDefault();
        let payload = {
            fullname: $('#regFullname').val(),
            username: $('#regUsername').val(),
            password: $('#regPassword').val(),
            role: $('#regRole').val()
        };
        fetch('/api/register', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        }).then(r=>r.json()).then(data=>{
            if(data.success) {
                alert(data.message);
                $('#registerModal').modal('hide');
                $('#registerForm')[0].reset();
            } else {
                alert(data.message);
            }
        }).catch(err => alert("Error connecting to server"));
    });
    
    // Child Case Submission
    $('#childCaseForm').submit(function(e) {
        e.preventDefault();
        let payload = {
            fullname: $('#cFName').val(), gender: $('#cFGender').val(), age: $('#cFAge').val(),
            grade: $('#cFGrade').val(), school: $('#cFSchool').val(), province: $('#cFProvince').val(),
            district: $('#cFDistrict').val(), subdistrict: $('#cFSubdistrict').val(), address: $('#cFAddress').val(),
            years_in_area: $('#cFYears').val(), survey_date: $('#cFDate').val(), water_source: $('#cFWater').val(),
            water_source_other: $('#cFWaterOther').val(), deans_index: $('#cFDeanIndex').val(),
            created_by: sessionStorage.getItem('userName'),
            u1:$('#cFU1').val(), u2:$('#cFU2').val(), u3:$('#cFU3').val(), u4:$('#cFU4').val(), u5:$('#cFU5').val(), u6:$('#cFU6').val(), u7:$('#cFU7').val(),
            l1:$('#cFL1').val(), l2:$('#cFL2').val(), l3:$('#cFL3').val(), l4:$('#cFL4').val(), l5:$('#cFL5').val(), l6:$('#cFL6').val(), l7:$('#cFL7').val()
        };
        fetch('/api/cases/submit', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        }).then(r=>r.json()).then(data=>{
            if(data.success) {
                alert("บันทึกข้อมูลเรียบร้อยแล้ว");
                $('#childCaseForm')[0].reset();
            } else {
                alert("Error: " + data.message);
            }
        });
    });
    
    // Admin User Approval
    $('#btnRefreshUsers').click(loadAdminUsers);
});

function loadAdminUsers() {
    fetch('/api/admin/users').then(r=>r.json()).then(data => {
        if(data.success) {
            let html = '';
            data.users.forEach(u => {
                let badge = u.status === 'approved' ? '<span class="badge bg-success">อนุมัติแล้ว</span>' : (u.status === 'pending' ? '<span class="badge bg-warning">รออนุมัติ</span>' : '<span class="badge bg-danger">ปฏิเสธ</span>');
                html += `<tr>
                    <td>${u.id}</td>
                    <td>${u.fullname}</td>
                    <td>${u.username}</td>
                    <td><span class="badge bg-primary">${u.role}</span></td>
                    <td>${badge}</td>
                    <td>${new Date(u.created_at).toLocaleDateString('th-TH')}</td>
                    <td>
                        <button class="btn btn-sm btn-success me-1" onclick="changeUserStatus(${u.id}, 'approve')" ${u.status === 'approved' ? 'disabled' : ''}>อนุมัติ</button>
                        <button class="btn btn-sm btn-danger" onclick="changeUserStatus(${u.id}, 'reject')" ${u.status === 'rejected' ? 'disabled' : ''}>ระงับ</button>
                    </td>
                </tr>`;
            });
            $('#adminUsersTable tbody').html(html);
        }
    });
}

window.changeUserStatus = function(id, action) {
    if(confirm(`ต้องการ ${action === 'approve' ? 'อนุมัติ' : 'ระงับ'} ผู้ใช้งานนี้ใช่หรือไม่?`)) {
        fetch('/api/admin/users/approve', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({id: id, action: action})
        }).then(r=>r.json()).then(data=>{
            if(data.success) loadAdminUsers();
            else alert(data.message);
        });
    }
}
