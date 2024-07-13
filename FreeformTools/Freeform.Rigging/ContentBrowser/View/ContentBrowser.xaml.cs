namespace Freeform.Rigging.ContentBrowser
{
    using System;
    using System.Windows;
    using System.Diagnostics;
    using System.Windows.Interop;
    using static Freeform.Rigging.ContentBrowser.ContentBrowserVM;
    using Freeform.Core.UI;



    /// <summary>
    /// Interaction logic for ContentBrowser.xaml
    /// </summary>
    public partial class ContentBrowser : Window
    {
        public ContentBrowser()
        {
            InitializeComponent();
            SetupWindow();
            SetupDataContext();
        }

        public ContentBrowser(Process parent)
        {
            InitializeComponent();

            WindowInteropHelper helper = new WindowInteropHelper(this)
            {
                Owner = parent.MainWindowHandle
            };

            SetupWindow();
            SetupDataContext();
        }

        private void ContentBrowser_Closing(object sender, System.ComponentModel.CancelEventArgs e)
        {
            if (WindowState == WindowState.Maximized)
            {
                // Use the RestoreBounds as the current values will be 0, 0 and the size of the screen
                Properties.Settings.Default.ContentBrowserTop = RestoreBounds.Top;
                Properties.Settings.Default.ContentBrowserLeft = RestoreBounds.Left;
                Properties.Settings.Default.ContentBrowserHeight = RestoreBounds.Height;
                Properties.Settings.Default.ContentBrowserWidth = RestoreBounds.Width;
                Properties.Settings.Default.ContentBrowserMaximized = true;
                Properties.Settings.Default.ContentBrowserIconSize = (DataContext as ContentBrowserVM).IconWidth;

                Properties.Settings.Default.ContentBrowserFilterFBX = (DataContext as ContentBrowserVM).FilterFiles;
                Properties.Settings.Default.ContentBrowserFilterFBX = (DataContext as ContentBrowserVM).FilterFolders;

                Properties.Settings.Default.ContentBrowserFilterMA = (DataContext as ContentBrowserVM).FilterMA;
                Properties.Settings.Default.ContentBrowserFilterMAX = (DataContext as ContentBrowserVM).FilterMAX;
                Properties.Settings.Default.ContentBrowserFilterFBX = (DataContext as ContentBrowserVM).FilterFBX;

                Properties.Settings.Default.ContentBrowserFilterFBX = (DataContext as ContentBrowserVM).FilterAllImageFiles;
                Properties.Settings.Default.ContentBrowserFilterFBX = (DataContext as ContentBrowserVM).FilterPSD;
                Properties.Settings.Default.ContentBrowserFilterFBX = (DataContext as ContentBrowserVM).FilterTGA;
                Properties.Settings.Default.ContentBrowserFilterFBX = (DataContext as ContentBrowserVM).FilterPNG;
                Properties.Settings.Default.ContentBrowserFilterFBX = (DataContext as ContentBrowserVM).FilterJPG;
                Properties.Settings.Default.ContentBrowserViewState = (int)(DataContext as ContentBrowserVM).UIViewState;
            }
            else
            {
                Properties.Settings.Default.ContentBrowserTop = Top;
                Properties.Settings.Default.ContentBrowserLeft = Left;
                Properties.Settings.Default.ContentBrowserHeight = Height;
                Properties.Settings.Default.ContentBrowserWidth = Width;
                Properties.Settings.Default.ContentBrowserMaximized = false;
                Properties.Settings.Default.ContentBrowserIconSize = (DataContext as ContentBrowserVM).IconWidth;

                Properties.Settings.Default.ContentBrowserFilterFiles = (DataContext as ContentBrowserVM).FilterFiles;
                Properties.Settings.Default.ContentBrowserFilterFolders = (DataContext as ContentBrowserVM).FilterFolders;

                Properties.Settings.Default.ContentBrowserFilterMA = (DataContext as ContentBrowserVM).FilterMA;
                Properties.Settings.Default.ContentBrowserFilterMAX = (DataContext as ContentBrowserVM).FilterMAX;
                Properties.Settings.Default.ContentBrowserFilterFBX = (DataContext as ContentBrowserVM).FilterFBX;

                Properties.Settings.Default.ContentBrowserFilterAllImages = (DataContext as ContentBrowserVM).FilterAllImageFiles;
                Properties.Settings.Default.ContentBrowserFilterPSD = (DataContext as ContentBrowserVM).FilterPSD;
                Properties.Settings.Default.ContentBrowserFilterTGA = (DataContext as ContentBrowserVM).FilterTGA;
                Properties.Settings.Default.ContentBrowserFilterPNG = (DataContext as ContentBrowserVM).FilterPNG;
                Properties.Settings.Default.ContentBrowserFilterJPG = (DataContext as ContentBrowserVM).FilterJPG;
                Properties.Settings.Default.ContentBrowserViewState = (int)(DataContext as ContentBrowserVM).UIViewState;
            }

            Properties.Settings.Default.Save();
        }

        void SetupWindow()
        {
            Top = Properties.Settings.Default.ContentBrowserTop;
            Left = Properties.Settings.Default.ContentBrowserLeft;
            Height = Properties.Settings.Default.ContentBrowserHeight;
            Width = Properties.Settings.Default.ContentBrowserWidth;
            if (Properties.Settings.Default.ContentBrowserMaximized)
            {
                WindowState = WindowState.Maximized;
            }
        }

        void SetupDataContext()
        {
            DispatcherHelper.UIDispatcher = Dispatcher;

            ContentBrowserVM vm = new ContentBrowserVM
            {
                IconWidth = Properties.Settings.Default.ContentBrowserIconSize,

                FilterFiles = Properties.Settings.Default.ContentBrowserFilterFiles,
                FilterFolders = Properties.Settings.Default.ContentBrowserFilterFolders,

                FilterMA = Properties.Settings.Default.ContentBrowserFilterMA,
                FilterMAX = Properties.Settings.Default.ContentBrowserFilterMAX,
                FilterFBX = Properties.Settings.Default.ContentBrowserFilterFBX,

                FilterAllImageFiles = Properties.Settings.Default.ContentBrowserFilterAllImages,
                FilterPSD = Properties.Settings.Default.ContentBrowserFilterPSD,
                FilterTGA = Properties.Settings.Default.ContentBrowserFilterTGA,
                FilterPNG = Properties.Settings.Default.ContentBrowserFilterPNG,
                FilterJPG = Properties.Settings.Default.ContentBrowserFilterJPG,
                UIViewState = (ViewState)Properties.Settings.Default.ContentBrowserViewState
            };

            DataContext = vm;
            if (vm.CloseAction == null)
            {
                vm.CloseAction = new Action(Close);
            }
        }

        protected override void OnClosed(EventArgs e)
        {
            base.OnClosed(e);
            ContentBrowserVM vm = DataContext as ContentBrowserVM;
            vm.Close();
        }

        private void BrowseBack_Executed(object sender, System.Windows.Input.ExecutedRoutedEventArgs e)
        {
            (DataContext as ContentBrowserVM).HistoryBackCall(null);
        }

        private void BrowseForward_Executed(object sender, System.Windows.Input.ExecutedRoutedEventArgs e)
        {
            (DataContext as ContentBrowserVM).HistoryForwardCall(null);
        }

        private void Window_Drop(object sender, DragEventArgs e)
        {
            if (e.Data.GetDataPresent(DataFormats.FileDrop))
            {
                string[] files = (string[])e.Data.GetData(DataFormats.FileDrop);
                (DataContext as ContentBrowserVM).NavigateToPath(files[0]);
            }
            else if (e.Data.GetDataPresent(DataFormats.StringFormat))
            {
                string file = (string)e.Data.GetData(DataFormats.StringFormat);
                (DataContext as ContentBrowserVM).NavigateToPath(file);
            }
        }
    }
}
